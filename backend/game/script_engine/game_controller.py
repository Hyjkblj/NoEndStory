"""游戏控制器：主循环、状态管理

负责：
- 初始化游戏
- 处理玩家选择
- 协调规则引擎、剧本管理器、AI 创作层
- 管理事件生命周期
"""
from typing import Optional
from .models import (
    GameState, EmotionState, PlayerOption, EventDraft,
    EventSummary, KeyBeat, OpeningEvent,
)
from .rule_engine import RuleEngine
from .script_manager import ScriptManager
from .ai_creator import AICreator
from utils.logger import get_logger

logger = get_logger(__name__)


class GameController:
    """游戏控制器"""

    def __init__(self, llm_service=None):
        self.rule_engine = RuleEngine()
        self.script_manager = ScriptManager()
        self.ai_creator = AICreator(llm_service)

    def initialize_game(
        self,
        thread_id: str,
        character_id: int,
        character_name: str,
        character_personality: list[str],
        scene_id: str,
        opening_events_pool: Optional[list] = None,
    ) -> GameState:
        """初始化游戏

        Args:
            thread_id: 会话 ID
            character_id: 角色 ID
            character_name: 角色名
            character_personality: 性格关键词列表
            scene_id: 场景 ID
            opening_events_pool: 场景的开场事件池

        Returns:
            初始化后的 GameState
        """
        # 1. 创建初始情绪状态
        initial_emotion = EmotionState()

        # 2. 从场景事件池选取开场事件
        opening_event = self.script_manager.select_opening_event(
            scene_id, opening_events_pool
        )

        # 3. 构建事件 0 的 KeyBeat[0]（轮次 1，预设内容）
        event_0 = EventDraft(
            draft_id="event_0",
            title=opening_event.title,
            scene=opening_event.scene,
            narrative_beat="opening",
            brief_description=opening_event.description,
            key_beats=[
                KeyBeat(
                    beat_index=0,
                    trigger_round=0,
                    narrative_content=opening_event.description,
                    emotion_target_range={"favorability": [45, 60]},
                    option_directions=opening_event.option_directions,
                    scene_mood=opening_event.mood,
                )
            ],
            emotion_direction={"favorability": "up", "trust": "up"},
            estimated_rounds=3,
            detail_level="full",
            opening_event=opening_event,
        )

        # 4. 初始化剧本（叙事锚点 + 事件 1-3 简略草案）
        self.script_manager.initialize_script(scene_id, character_personality, initial_emotion)

        # 5. 创建游戏状态
        state = GameState(
            thread_id=thread_id,
            character_id=character_id,
            character_name=character_name,
            character_personality=character_personality,
            scene_id=scene_id,
            emotion=initial_emotion,
            current_event=event_0,
            current_beat_index=0,
            current_event_rounds=0,
            dialogue_history=[],
            current_options=[],
            draft_queue=self.script_manager.draft_queue,
            completed_events=[],
            narrative_anchor=self.script_manager.narrative_anchor,
            total_rounds=0,
            total_events=0,
            is_finished=False,
        )

        # 6. 生成第一轮选项
        first_beat = event_0.key_beats[0]
        state_changes = self.rule_engine.generate_option_state_changes(
            first_beat.option_directions, initial_emotion
        )
        state.current_options = [
            PlayerOption(id=i, text=text, state_changes=sc)
            for i, (text, sc) in enumerate(zip(first_beat.option_directions, state_changes))
        ]

        logger.info(f"游戏初始化完成: {opening_event.title}")
        return state

    def process_player_choice(
        self,
        state: GameState,
        option_id: int,
    ) -> GameState:
        """处理玩家选择

        Args:
            state: 当前游戏状态
            option_id: 玩家选择的选项 ID

        Returns:
            更新后的 GameState
        """
        # 1. 获取玩家选项
        if option_id < 0 or option_id >= len(state.current_options):
            logger.warning(f"无效的选项 ID: {option_id}")
            return state

        option = state.current_options[option_id]

        # 2. 记录对话历史
        state.dialogue_history.append({'role': 'user', 'content': option.text})

        # 3. 规则引擎：计算情绪变化
        current_beat = self._get_current_beat(state)
        state.emotion = self.rule_engine.calculate_emotion_change(
            current=state.emotion,
            option_state_changes=option.state_changes,
            narrative_beat=state.current_event.narrative_beat if state.current_event else 'rising',
            beat_emotion_target=current_beat.emotion_target_range if current_beat else None,
        )

        # 4. 更新轮次计数
        state.current_event_rounds += 1
        state.total_rounds += 1

        # 5. 事件 0 轮次 1 结束后：生成剩余 KeyBeat
        if (state.current_event and
            state.current_event.opening_event and
            state.current_event_rounds == 1 and
            len(state.current_event.key_beats) == 1):
            self._generate_remaining_beats_for_event_0(state)

        # 6. 规则引擎：判定事件是否结束
        should_end, reason = self.rule_engine.should_advance_event(
            current_round=state.current_event_rounds,
            event=state.current_event,
            emotion=state.emotion,
        )

        if should_end:
            return self._handle_event_end(state, reason)

        # 7. 生成下一轮内容
        return self._generate_next_round(state)

    def _generate_remaining_beats_for_event_0(self, state: GameState) -> None:
        """事件 0 轮次 1 结束后，生成剩余 KeyBeat"""
        opening = state.current_event.opening_event
        last_choice = state.dialogue_history[-1]['content'] if state.dialogue_history else ""

        beats = self.ai_creator.generate_key_beats_for_event_0(
            opening_title=opening.title,
            opening_description=opening.description,
            player_first_choice=last_choice,
            current_emotion=state.emotion,
        )

        state.current_event.key_beats.extend(beats)
        logger.info(f"事件 0 生成了 {len(beats)} 个额外 KeyBeat")

    def _generate_next_round(self, state: GameState) -> GameState:
        """生成下一轮台词和选项"""
        # 获取下一个 KeyBeat
        state.current_beat_index += 1
        beat = self._get_current_beat(state)

        if not beat:
            # 没有更多 KeyBeat，强制结束事件
            return self._handle_event_end(state, "KeyBeat 耗尽")

        # AI 生成台词
        last_choice = state.dialogue_history[-1]['content'] if state.dialogue_history else ""
        dialogue = self.ai_creator.generate_dialogue(
            beat=beat,
            player_last_choice=last_choice,
            dialogue_history=state.dialogue_history,
            character_name=state.character_name,
            character_personality=state.character_personality,
            current_emotion=state.emotion,
        )

        state.dialogue_history.append({'role': 'assistant', 'content': dialogue})

        # 生成选项
        state_changes = self.rule_engine.generate_option_state_changes(
            beat.option_directions, state.emotion
        )
        state.current_options = self.ai_creator.generate_options(
            option_directions=beat.option_directions,
            state_changes_presets=state_changes,
            current_emotion=state.emotion,
            character_name=state.character_name,
        )

        return state

    def _handle_event_end(self, state: GameState, reason: str) -> GameState:
        """处理事件结束"""
        logger.info(f"事件结束: {reason}")

        # 1. 创建事件摘要
        summary = EventSummary(
            event_id=state.current_event.draft_id if state.current_event else "unknown",
            title=state.current_event.title if state.current_event else "未知",
            scene=state.current_event.scene if state.current_event else state.scene_id,
            rounds_played=state.current_event_rounds,
            key_events=self._summarize_event(state),
            emotion_changes=self._calc_emotion_changes(state),
        )
        state.completed_events.append(summary)

        # 2. 检查锚点达成
        self.script_manager.check_anchor_achievement(state.emotion)

        # 3. 规则引擎：判定是否触发结局
        anchor_progress = self.script_manager.get_anchor_progress()
        should_end, end_reason, ending_type = self.rule_engine.should_trigger_ending(
            total_rounds=state.total_rounds,
            total_events=state.total_events + 1,
            emotion=state.emotion,
            narrative_beat=state.current_event.narrative_beat if state.current_event else 'rising',
            anchor_progress=anchor_progress,
        )

        if should_end:
            return self._handle_ending(state, end_reason, ending_type)

        # 4. 推进剧本
        self.script_manager.advance_script(summary)
        state.draft_queue = self.script_manager.draft_queue
        state.total_events += 1

        # 5. 激活下一个事件
        return self._activate_next_event(state)

    def _activate_next_event(self, state: GameState) -> GameState:
        """激活下一个事件"""
        if not state.draft_queue:
            return self._handle_ending(state, "草案队列为空", "open_ending")

        next_draft = state.draft_queue[0]

        # 如果需要升级（从简略版升级为完整版）
        if next_draft.detail_level == "pending_upgrade":
            next_draft = self._upgrade_draft(next_draft, state)

        state.current_event = next_draft
        state.current_beat_index = 0
        state.current_event_rounds = 0
        state.dialogue_history = []

        # 生成第一轮内容
        if next_draft.key_beats:
            beat = next_draft.key_beats[0]
            state_changes = self.rule_engine.generate_option_state_changes(
                beat.option_directions, state.emotion
            )
            state.current_options = self.ai_creator.generate_options(
                option_directions=beat.option_directions,
                state_changes_presets=state_changes,
                current_emotion=state.emotion,
                character_name=state.character_name,
            )
        else:
            # 需要 AI 生成 KeyBeat
            draft = self.ai_creator.generate_event_draft(
                anchor_theme=self.script_manager.narrative_anchor.theme if self.script_manager.narrative_anchor else "校园故事",
                beat_type=next_draft.narrative_beat,
                recent_summaries=state.completed_events,
                current_emotion=state.emotion,
                scene_id=next_draft.scene,
            )
            state.current_event = draft
            if draft.key_beats:
                beat = draft.key_beats[0]
                state_changes = self.rule_engine.generate_option_state_changes(
                    beat.option_directions, state.emotion
                )
                state.current_options = self.ai_creator.generate_options(
                    option_directions=beat.option_directions,
                    state_changes_presets=state_changes,
                    current_emotion=state.emotion,
                    character_name=state.character_name,
                )

        return state

    def _upgrade_draft(self, draft: EventDraft, state: GameState) -> EventDraft:
        """升级草案为完整版"""
        full_draft = self.ai_creator.generate_event_draft(
            anchor_theme=self.script_manager.narrative_anchor.theme if self.script_manager.narrative_anchor else "校园故事",
            beat_type=draft.narrative_beat,
            recent_summaries=state.completed_events,
            current_emotion=state.emotion,
            scene_id=draft.scene,
        )
        full_draft.draft_id = draft.draft_id
        full_draft.detail_level = "full"
        return full_draft

    def _handle_ending(self, state: GameState, reason: str, ending_type: str) -> GameState:
        """处理结局"""
        logger.info(f"触发结局: {reason}, 类型: {ending_type}")
        state.is_finished = True
        state.ending_type = ending_type
        state.current_options = []  # 结局无选项
        return state

    def _get_current_beat(self, state: GameState) -> Optional[KeyBeat]:
        """获取当前 KeyBeat"""
        if state.current_event and state.current_event.key_beats:
            if state.current_beat_index < len(state.current_event.key_beats):
                return state.current_event.key_beats[state.current_beat_index]
        return None

    def _summarize_event(self, state: GameState) -> str:
        """生成事件摘要"""
        if not state.dialogue_history:
            return "无对话记录"

        # 取最后 2 轮对话作为摘要
        recent = state.dialogue_history[-4:]
        lines = []
        for msg in recent:
            role = "玩家" if msg.get('role') == 'user' else "角色"
            lines.append(f"{role}: {msg.get('content', '')[:30]}")
        return " | ".join(lines)

    def _calc_emotion_changes(self, state: GameState) -> dict:
        """计算情绪变化（简化版）"""
        return {
            "favorability": state.emotion.favorability - 50,
            "trust": state.emotion.trust - 50,
        }
