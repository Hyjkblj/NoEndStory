"""AI 创作层：只负责创作，不负责决策

职责：
- 生成台词（在节拍范围内）
- 生成选项文本
- 生成草案描述
- 生成 KeyBeat
"""
from typing import Optional
from .models import KeyBeat, EmotionState, PlayerOption, EventDraft, EventSummary
from utils.logger import get_logger

logger = get_logger(__name__)


class AICreator:
    """AI 创作层"""

    def __init__(self, llm_service=None):
        self.llm = llm_service

    def set_llm_service(self, llm_service):
        self.llm = llm_service

    def generate_dialogue(
        self,
        beat: KeyBeat,
        player_last_choice: str,
        dialogue_history: list,
        character_name: str,
        character_personality: list[str],
        current_emotion: EmotionState,
    ) -> str:
        """生成角色台词"""
        if not self.llm:
            return f"{character_name}：..."

        history_text = self._format_history(dialogue_history[-4:])

        prompt = f"""你是{character_name}，性格：{'、'.join(character_personality)}。

当前剧情：{beat.narrative_content}
氛围：{beat.scene_mood}

对话历史：
{history_text}

玩家刚才说/做了：{player_last_choice}

你的情绪：好感度{current_emotion.favorability:.0f}，信任度{current_emotion.trust:.0f}

请用符合你性格的方式回复，50-100字。不要加旁白和动作描述。"""

        try:
            result = self._call_llm(prompt, max_tokens=150, temperature=0.85)
            return result if result else f"{character_name}：嗯..."
        except Exception as e:
            logger.warning(f"台词生成失败: {e}")
            return f"{character_name}：..."

    def generate_options(
        self,
        option_directions: list[str],
        state_changes_presets: list[dict],
        current_emotion: EmotionState,
        character_name: str,
    ) -> list[PlayerOption]:
        """生成玩家选项文本"""
        if not self.llm:
            return [
                PlayerOption(id=i, text=dir, state_changes=sc)
                for i, (dir, sc) in enumerate(zip(option_directions, state_changes_presets))
            ]

        prompt = f"""为玩家生成 3 个选项，每个选项 15-30 字。

选项方向：
1. {option_directions[0]}
2. {option_directions[1]}
3. {option_directions[2]}

当前情绪状态：好感度{current_emotion.favorability:.0f}，信任度{current_emotion.trust:.0f}

请直接输出 3 个选项，每行一个，不要编号。"""

        try:
            result = self._call_llm(prompt, max_tokens=100, temperature=0.8)
            if result:
                lines = [line.strip() for line in result.strip().split('\n') if line.strip()]
                options = []
                for i, text in enumerate(lines[:3]):
                    options.append(PlayerOption(
                        id=i,
                        text=text,
                        state_changes=state_changes_presets[i] if i < len(state_changes_presets) else {},
                    ))
                # 确保有 3 个选项
                while len(options) < 3:
                    idx = len(options)
                    options.append(PlayerOption(
                        id=idx,
                        text=option_directions[idx] if idx < len(option_directions) else "继续",
                        state_changes=state_changes_presets[idx] if idx < len(state_changes_presets) else {},
                    ))
                return options
        except Exception as e:
            logger.warning(f"选项生成失败: {e}")

        # 降级：使用方向文本作为选项
        return [
            PlayerOption(id=i, text=dir, state_changes=sc)
            for i, (dir, sc) in enumerate(zip(option_directions, state_changes_presets))
        ]

    def generate_key_beats_for_event_0(
        self,
        opening_title: str,
        opening_description: str,
        player_first_choice: str,
        current_emotion: EmotionState,
    ) -> list[KeyBeat]:
        """事件 0 轮次 1 结束后，生成剩余轮次的 KeyBeat"""
        if not self.llm:
            return [
                KeyBeat(
                    beat_index=1,
                    trigger_round=1,
                    narrative_content="对话继续深入",
                    emotion_target_range={"favorability": [45, 65]},
                    option_directions=["积极回应", "保持中性", "消极回应"],
                    scene_mood="自然",
                ),
                KeyBeat(
                    beat_index=2,
                    trigger_round=2,
                    narrative_content="事件自然收束",
                    emotion_target_range={"favorability": [50, 70]},
                    option_directions=["期待再见", "礼貌告别", "无所谓"],
                    scene_mood="温馨",
                ),
            ]

        prompt = f"""开场事件：{opening_title}
描述：{opening_description}
玩家第一个选择：{player_first_choice}
当前情绪：好感度{current_emotion.favorability:.0f}，信任度{current_emotion.trust:.0f}

请为这个事件设计 2 个后续关键节拍，JSON 格式输出：
[
  {{"narrative_content": "节拍内容", "mood": "氛围", "directions": ["选项方向1", "选项方向2", "选项方向3"]}},
  {{"narrative_content": "节拍内容", "mood": "氛围", "directions": ["选项方向1", "选项方向2", "选项方向3"]}}
]

要求：
- 第一个节拍推进关系，第二个节拍收束事件
- 选项方向要具体，符合角色性格"""

        try:
            import json
            result = self._call_llm(prompt, max_tokens=300, temperature=0.8)
            if result:
                # 尝试解析 JSON
                text = result.strip()
                if text.startswith('```'):
                    text = text.split('\n', 1)[1].rsplit('```', 1)[0]
                data = json.loads(text)
                beats = []
                for i, item in enumerate(data[:2]):
                    beats.append(KeyBeat(
                        beat_index=i + 1,
                        trigger_round=i + 1,
                        narrative_content=item.get('narrative_content', ''),
                        emotion_target_range={"favorability": [45, 70]},
                        option_directions=item.get('directions', ["积极回应", "保持中性", "消极回应"]),
                        scene_mood=item.get('mood', '自然'),
                    ))
                return beats
        except Exception as e:
            logger.warning(f"KeyBeat 生成失败: {e}")

        # 降级
        return self.generate_key_beats_for_event_0.__wrapped__(self) if hasattr(self.generate_key_beats_for_event_0, '__wrapped__') else [
            KeyBeat(beat_index=1, trigger_round=1, narrative_content="对话继续"),
            KeyBeat(beat_index=2, trigger_round=2, narrative_content="事件收束"),
        ]

    def generate_event_draft(
        self,
        anchor_theme: str,
        beat_type: str,
        recent_summaries: list[EventSummary],
        current_emotion: EmotionState,
        scene_id: str,
    ) -> EventDraft:
        """生成事件草案（简略版或完整版）"""
        recent_text = "\n".join([f"- {s.title}: {s.key_events}" for s in recent_summaries[-3:]])

        prompt = f"""故事主题：{anchor_theme}
当前叙事阶段：{beat_type}
场景：{scene_id}
最近事件：{recent_text or '（开局）'}
当前情绪：好感度{current_emotion.favorability:.0f}，信任度{current_emotion.trust:.0f}

请生成一个事件草案，JSON 格式：
{{"title": "事件标题", "description": "50-100字剧情描述", "mood": "氛围", "directions": ["选项方向1", "选项方向2", "选项方向3"]}}"""

        try:
            import json
            result = self._call_llm(prompt, max_tokens=200, temperature=0.8)
            if result:
                text = result.strip()
                if text.startswith('```'):
                    text = text.split('\n', 1)[1].rsplit('```', 1)[0]
                data = json.loads(text)
                return EventDraft(
                    draft_id=f"event_{len(recent_summaries) + 1}",
                    title=data.get('title', '继续'),
                    scene=scene_id,
                    narrative_beat=beat_type,
                    brief_description=data.get('description', ''),
                    estimated_rounds=3 if beat_type != 'climax' else 4,
                    detail_level="brief",
                )
        except Exception as e:
            logger.warning(f"草案生成失败: {e}")

        return EventDraft(
            draft_id=f"event_{len(recent_summaries) + 1}",
            title="继续",
            scene=scene_id,
            narrative_beat=beat_type,
            brief_description="故事继续发展。",
            detail_level="brief",
        )

    def _call_llm(self, prompt: str, max_tokens: int = 150, temperature: float = 0.8) -> Optional[str]:
        """调用 LLM"""
        try:
            from game.ai_generator import _get_text_gen
            ai_gen = _get_text_gen()
            if ai_gen and ai_gen.enabled:
                return ai_gen._call_text_generation(
                    prompt, max_tokens=max_tokens, temperature=temperature, call_type="script"
                )
        except Exception as e:
            logger.warning(f"LLM 调用失败: {e}")
        return None

    def _format_history(self, history: list) -> str:
        """格式化对话历史"""
        lines = []
        for msg in history[-4:]:
            role = msg.get('role', '')
            content = msg.get('content', '')
            if role == 'user':
                lines.append(f"玩家：{content}")
            elif role == 'assistant':
                lines.append(f"角色：{content}")
        return "\n".join(lines) if lines else "（对话开始）"
