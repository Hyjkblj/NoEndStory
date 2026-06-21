"""ScriptEngine V2 — 大脑 + 导演

内部模块：
  - NarrativePlanner: 叙事节拍管理
  - EndingJudge: 结局判断
  - EventManager: 事件生命周期
  - SceneGenerator: 场景生成
  - DialogueGenerator: 台词生成（LLM）
  - OptionGenerator: 选项生成（LLM + 规则）
  - EmotionCalculator: 数值变化计算
"""
import json
import random
import re
from typing import Dict, List, Optional, Any
from utils.logger import get_logger
from .models import RoundOutput, Option

logger = get_logger("script_engine_v2")


# ============================================================
# NarrativePlanner — 叙事节拍管理
# ============================================================

class NarrativePlanner:
    """叙事节拍管理"""

    BEATS = [
        {"name": "开场相识", "phase": "opening", "start": 0, "end": 5,
         "emotion_target": "neutral_warm",
         "event_pool": ["first_meeting", "casual_chat", "mutual_introduction"]},
        {"name": "关系建立", "phase": "rising", "start": 5, "end": 13,
         "emotion_target": "growing_close",
         "event_pool": ["shared_activity", "small_conflict", "personal_revelation", "help_moment"]},
        {"name": "冲突爆发", "phase": "climax", "start": 13, "end": 23,
         "emotion_target": "intense",
         "event_pool": ["major_conflict", "critical_choice", "emotional_confession", "betrayal"]},
        {"name": "冲突化解", "phase": "resolution", "start": 23, "end": 30,
         "emotion_target": "resolution",
         "event_pool": ["reconciliation", "final_choice", "departure", "promise"]},
    ]

    def get_current_beat(self, elapsed_minutes: float) -> dict:
        for beat in self.BEATS:
            if beat["start"] <= elapsed_minutes < beat["end"]:
                return beat
        return self.BEATS[-1]

    def get_phase(self, elapsed_minutes: float) -> str:
        return self.get_current_beat(elapsed_minutes)["phase"]


# ============================================================
# EndingJudge — 结局判断
# ============================================================

class EndingJudge:
    """结局判断"""

    def should_end(self, elapsed_minutes: float, total_rounds: int,
                   emotion) -> tuple:
        """判断是否应该结束

        Returns:
            (是否结束, 原因)
        """
        # 硬上限
        if elapsed_minutes >= 30.0:
            return True, "time_exceeded"
        if total_rounds >= 25:
            return True, "rounds_exceeded"

        # 情绪极化（至少 8 轮后）
        if total_rounds >= 8:
            if emotion.favorability >= 85 and emotion.trust >= 75 and emotion.happiness >= 70:
                return True, "happy_ending_early"
            if emotion.hostility >= 70:
                return True, "hostility_extreme"
            if emotion.favorability <= 15 and emotion.trust <= 20:
                return True, "relationship_collapse"

        return False, "continue"

    def classify_ending(self, emotion) -> str:
        """分类结局类型"""
        if emotion.favorability >= 70 and emotion.hostility <= 20:
            return "happy_ending"
        if emotion.hostility >= 50 or emotion.favorability <= 20:
            return "bad_ending"
        if emotion.favorability >= 40 and emotion.trust >= 50:
            return "neutral_ending"
        return "open_ending"


# ============================================================
# EventManager — 事件生命周期
# ============================================================

class EventManager:
    """事件生命周期管理"""

    EVENT_TEMPLATES = {
        "first_meeting": "角色与玩家初次相遇",
        "casual_chat": "角色与玩家闲聊日常",
        "mutual_introduction": "角色与玩家互相介绍",
        "shared_activity": "角色与玩家共同完成某件事",
        "small_conflict": "角色与玩家产生小误会",
        "personal_revelation": "角色向玩家透露个人秘密",
        "help_moment": "角色帮助玩家解决一个困难",
        "major_conflict": "角色与玩家发生严重分歧",
        "critical_choice": "角色面临关键抉择",
        "emotional_confession": "角色情感爆发表白",
        "betrayal": "角色感到被背叛",
        "reconciliation": "角色与玩家和解",
        "final_choice": "角色做出最终决定",
        "departure": "角色准备离开",
        "promise": "角色做出承诺",
    }

    def select_event(self, beat: dict, used_events: set, emotion) -> str:
        """选择事件（情绪驱动 + 去重）"""
        available = [e for e in beat.get("event_pool", []) if e not in used_events]
        if not available:
            available = beat.get("event_pool", list(self.EVENT_TEMPLATES.keys()))

        # 情绪驱动偏向
        if emotion.favorability >= 70:
            positive = ["shared_activity", "personal_revelation", "help_moment", "promise"]
            weighted = [e for e in available if e in positive]
            if weighted:
                return random.choice(weighted)

        if emotion.hostility >= 40:
            negative = ["small_conflict", "major_conflict", "betrayal"]
            weighted = [e for e in available if e in negative]
            if weighted:
                return random.choice(weighted)

        return random.choice(available) if available else "casual_chat"

    def should_advance_event(self, round_count: int, min_rounds: int = 2,
                             max_rounds: int = 5) -> bool:
        """判断事件是否应该结束"""
        if round_count < min_rounds:
            return False
        if round_count >= max_rounds:
            return True
        if round_count >= 3:
            prob = (round_count - 2) * 0.3
            return random.random() < prob
        return False

    def get_event_description(self, event_type: str) -> str:
        return self.EVENT_TEMPLATES.get(event_type, "角色与玩家互动")


# ============================================================
# SceneGenerator — 场景生成
# ============================================================

class SceneGenerator:
    """场景生成"""

    def __init__(self, scenes_data: dict = None):
        self.scenes_data = scenes_data or {}

    def select_scene(self, current_scene: str, event_type: str,
                     elapsed_minutes: float) -> str:
        """选择场景"""
        if random.random() < 0.7:
            return current_scene
        available = [s for s in self.scenes_data if s != current_scene]
        return random.choice(available) if available else current_scene


# ============================================================
# DialogueGenerator — 台词生成（LLM）
# ============================================================

class DialogueGenerator:
    """台词生成"""

    def __init__(self, llm_tool=None):
        self.llm = llm_tool

    async def generate(self, state, event_description: str) -> str:
        """生成角色台词"""
        prompt = self._build_prompt(state, event_description)

        if self.llm:
            try:
                logger.info(f"[LLM台词] 开始生成: prompt长度={len(prompt)}, character={state.character_name}")
                result = await self.llm.generate(
                    prompt, max_tokens=100, temperature=0.9, call_type="dialogue"
                )
                logger.info(f"[LLM台词] 生成完成: result长度={len(result) if result else 0}, 前50字={result[:50] if result else 'None'}")
                if result and self._has_readable_text(result):
                    return result.strip()
                logger.warning("[LLM台词] 返回空结果或不可读文本，使用回退文本")
            except Exception as e:
                logger.warning(f"[LLM台词] 生成异常: {e}", exc_info=True)
        else:
            logger.warning("[LLM台词] LLM未初始化，使用回退文本")

        return self._fallback_dialogue(state, event_description)

    def _fallback_dialogue(self, state, event_description: str) -> str:
        name = state.character_name or "角色"
        last_input = (getattr(state, "last_player_input", "") or "").strip()

        if last_input and not last_input.startswith("["):
            return f"{name}: 我听见了。只是这一刻有点突然，让我想把你的话再认真想一想。"

        if "初次" in event_description or "介绍" in event_description:
            return f"{name}: 没想到会在这里遇见你。刚才有点走神，不过看到你来了，心里反而安定了一点。"

        if "冲突" in event_description or "误会" in event_description or "分歧" in event_description:
            return f"{name}: 我不是想把气氛弄僵，只是有些话如果不说清楚，我会一直在意。"

        if "秘密" in event_description or "透露" in event_description:
            return f"{name}: 这件事我很少和别人说，但如果是你的话，我好像愿意多相信一点。"

        return f"{name}: 刚刚那一瞬间，我有点不知道该怎么开口。你愿意再陪我待一会儿吗？"

    def _has_readable_text(self, text: str) -> bool:
        return bool(re.search(r"[\w\u4e00-\u9fff]", text or ""))

    def _build_prompt(self, state, event_description: str) -> str:
        """构建 prompt"""
        emotion = state.emotion
        world = state.world
        personality = state.character_personality.get("keywords", [])

        parts = [
            f"你是{state.character_name}，性格：{'、'.join(personality) if personality else '普通'}。",
            f"场景：{world.current_scene}，时间：{world.current_time}，天气：{world.weather}。",
            f"当前事件：{event_description}。",
            "",
            "你的情绪状态：",
            f"- 好感度：{emotion.favorability:.0f}/100",
            f"- 信任度：{emotion.trust:.0f}/100",
            f"- 快乐：{emotion.happiness:.0f}/100",
            f"- 压力：{emotion.stress:.0f}/100",
        ]

        # 注入长期记忆
        if state.event_summaries:
            parts.append("")
            parts.append("之前的事件：")
            for i, s in enumerate(state.event_summaries[-3:], 1):
                parts.append(f"{i}. {s}")

        if state.knowledge:
            parts.append("")
            parts.append("你对玩家的了解：")
            for k in state.knowledge[:3]:
                parts.append(f"- {k.get('content', '')}")

        # 注入短期记忆
        recent = state.dialogue_history[-6:]
        if recent:
            parts.append("")
            parts.append("最近对话：")
            for msg in recent:
                role = "玩家" if msg.get("role") == "player" else state.character_name
                parts.append(f"{role}: {msg.get('content', '')}")

        parts.append("")
        parts.append(f"请以{state.character_name}的口吻回复一句话（20-80字），符合当前情绪和剧情。")

        return "\n".join(parts)


# ============================================================
# OptionGenerator — 选项生成（LLM + 规则）
# ============================================================

class OptionGenerator:
    """选项生成"""

    DEFAULT_OPTIONS = [
        Option(id=0, text="温柔回应，主动靠近一点", direction="positive",
               state_changes={"favorability": 5, "trust": 3, "happiness": 3}),
        Option(id=1, text="先听TA说完，再轻声追问", direction="neutral",
               state_changes={"favorability": 1, "trust": 1}),
        Option(id=2, text="保持距离，只给出简短回应", direction="negative",
               state_changes={"favorability": -3, "trust": -2, "stress": 2}),
    ]

    def __init__(self, llm_tool=None):
        self.llm = llm_tool

    async def generate(self, state, dialogue: str) -> List[Option]:
        """生成玩家选项"""
        if self.llm:
            options = await self._generate_with_llm(state, dialogue)
            if options:
                return options
        return self._fallback_options(state, dialogue)

    async def _generate_with_llm(self, state, dialogue: str) -> List[Option]:
        """LLM 生成选项"""
        try:
            prompt = f"""根据以下对话，为恋爱剧情游戏玩家生成 3 个回复选项。

角色台词：{dialogue}
当前情绪：好感度{state.emotion.favorability:.0f}，信任度{state.emotion.trust:.0f}

要求：
1. 每个选项 10-24 个中文字，必须像玩家真正会点击的回复
2. 第一个偏积极，第二个偏中性，第三个偏疏离或消极
3. 必须回应角色台词和当前情绪，不要脱离场景
4. 不要输出“积极回应”“中性回应”“消极回应”这类标签
5. 只输出 JSON 数组，例如 ["我会陪着你。","先听你说完。","这件事先到这里吧。"]"""

            result = await self.llm.generate(
                prompt, max_tokens=100, temperature=0.8, call_type="options"
            )

            if result:
                lines = self._parse_option_lines(result)
                if len(lines) >= 3:
                    return [
                        Option(id=0, text=lines[0], direction="positive",
                               state_changes={"favorability": 5, "trust": 3, "happiness": 3}),
                        Option(id=1, text=lines[1], direction="neutral",
                               state_changes={"favorability": 1, "trust": 1}),
                        Option(id=2, text=lines[2], direction="negative",
                               state_changes={"favorability": -3, "trust": -2, "stress": 2}),
                    ]
                logger.warning(f"LLM 选项结果不足 3 条，使用上下文降级选项: {result[:120]}")
        except Exception as e:
            logger.warning(f"LLM 选项生成失败: {e}", exc_info=True)

        return []

    def _parse_option_lines(self, result: str) -> List[str]:
        """解析 LLM 选项输出，兼容编号、项目符号和 JSON。"""
        candidates: List[str] = []

        json_candidates = [result.strip()]
        fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", result, flags=re.IGNORECASE | re.DOTALL)
        if fence_match:
            json_candidates.insert(0, fence_match.group(1).strip())
        array_match = re.search(r"\[[\s\S]*\]", result)
        if array_match:
            json_candidates.insert(0, array_match.group(0).strip())

        for candidate in json_candidates:
            try:
                data = json.loads(candidate)
            except (json.JSONDecodeError, TypeError, ValueError):
                continue

            if isinstance(data, list):
                candidates.extend(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in data)
            elif isinstance(data, dict):
                for key in ("options", "player_options", "choices"):
                    value = data.get(key)
                    if isinstance(value, list):
                        candidates.extend(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in value)
                        break

            if candidates:
                break

        if not candidates:
            candidates = [line for line in re.split(r"[\r\n]+", result) if line.strip()]

        parsed: List[str] = []
        for item in candidates:
            text = self._clean_option_text(item)
            if not text:
                continue
            if self._is_generic_option_label(text):
                continue
            if len(text) > 36:
                text = text[:36].rstrip("，。！？、 ")
            if text not in parsed:
                parsed.append(text)
            if len(parsed) >= 3:
                break

        return parsed

    def _clean_option_text(self, text: str) -> str:
        text = str(text).strip()
        text = re.sub(r"^\s*(?:[-*•]|[0-9一二三][\.、:：)]|选项\s*[0-9一二三]?\s*[：:])\s*", "", text)
        text = re.sub(r"^(?:积极回应|中性回应|消极回应|正向回应|负向回应|保持中性)\s*[：:，,、\-]\s*", "", text)
        text = text.strip("「」『』“”\"'` ")
        return text.strip()

    def _is_generic_option_label(self, text: str) -> bool:
        compact = re.sub(r"[\s：:，,。.!！?？、\-]+", "", text or "")
        return compact in {"积极回应", "中性回应", "消极回应", "正向回应", "负向回应", "保持中性"}

    def _fallback_options(self, state, dialogue: str) -> List[Option]:
        """LLM 不可用时的上下文降级选项，避免前端出现抽象标签。"""
        topic = self._extract_topic(dialogue)
        event_type = (state.pending_event or {}).get("type", "")

        if event_type in {"first_meeting", "mutual_introduction", "casual_chat"}:
            texts = [
                "自然打招呼，问TA刚才在想什么",
                "先点头回应，聊聊此刻的场景",
                "礼貌回应后，暂时保持一点距离",
            ]
        elif event_type in {"small_conflict", "major_conflict", "betrayal"}:
            texts = [
                "先放低声音，认真问TA在意什么",
                "暂时停下来，给彼此一点整理时间",
                "把情绪收回去，只留下简短回应",
            ]
        elif event_type in {"personal_revelation", "emotional_confession"}:
            texts = [
                "接住TA的心意，告诉TA你在听",
                "轻声追问这件事对TA意味着什么",
                "避开太深的话题，先保持距离",
            ]
        elif topic:
            texts = [
                f"围绕“{topic}”回应，靠近TA一点",
                f"先问清“{topic}”，观察TA的反应",
                "简单点头，把话题轻轻带过",
            ]
        else:
            texts = [
                "温柔回应，主动靠近一点",
                "先听TA说完，再轻声追问",
                "保持距离，只给出简短回应",
            ]

        return [
            Option(id=0, text=texts[0], direction="positive",
                   state_changes={"favorability": 5, "trust": 3, "happiness": 3}),
            Option(id=1, text=texts[1], direction="neutral",
                   state_changes={"favorability": 1, "trust": 1}),
            Option(id=2, text=texts[2], direction="negative",
                   state_changes={"favorability": -3, "trust": -2, "stress": 2}),
        ]

    def _extract_topic(self, dialogue: str) -> str:
        text = re.sub(r"^[^:：]+[：:]", "", dialogue or "").strip()
        text = re.sub(r"[。！？!?…\.]+$", "", text)
        text = re.sub(r"\s+", "", text)
        if not re.search(r"[\w\u4e00-\u9fff]", text):
            return ""
        return text[:8]


# ============================================================
# EmotionCalculator — 数值变化计算
# ============================================================

class EmotionCalculator:
    """数值变化计算"""

    STAGE_MULTIPLIER = {
        "opening": 0.6,
        "rising": 1.0,
        "climax": 1.5,
        "resolution": 0.8,
    }

    def calculate_changes(self, option: Option, phase: str,
                          character_personality: dict) -> Dict[str, float]:
        """计算数值变化"""
        base_changes = option.state_changes.copy()
        multiplier = self.STAGE_MULTIPLIER.get(phase, 1.0)

        # 应用阶段修正
        changes = {k: v * multiplier for k, v in base_changes.items()}

        # 应用性格修正
        changes = self._apply_personality(changes, character_personality)

        return changes

    def _apply_personality(self, changes: dict, personality: dict) -> dict:
        """性格修正"""
        keywords = personality.get("keywords", [])
        if not keywords:
            return changes

        modifiers = {
            "热情": {"favorability": 1.2, "happiness": 1.2},
            "高冷": {"favorability": 0.8, "happiness": 0.8},
            "温柔": {"favorability": 1.1, "trust": 1.1},
            "直率": {"favorability": 1.1, "stress": 1.1},
        }

        for keyword in keywords:
            if keyword in modifiers:
                for key, mult in modifiers[keyword].items():
                    if key in changes:
                        changes[key] = changes[key] * mult

        return changes


# ============================================================
# ScriptEngine — 主引擎
# ============================================================

class ScriptEngine:
    """ScriptEngine V2 — 大脑 + 导演

    生成所有交互数据：场景、台词、选项、数值变化、事件推进。
    """

    def __init__(self, llm_tool=None, scenes_data: dict = None):
        self.llm = llm_tool

        # 内部模块
        self.narrative_planner = NarrativePlanner()
        self.ending_judge = EndingJudge()
        self.event_manager = EventManager()
        self.scene_generator = SceneGenerator(scenes_data)
        self.dialogue_generator = DialogueGenerator(llm_tool)
        self.option_generator = OptionGenerator(llm_tool)
        self.emotion_calculator = EmotionCalculator()

    async def generate_round(self, state) -> RoundOutput:
        """生成一个完整轮次的所有交互数据

        这是 ScriptEngine 的核心方法，一次调用生成所有内容。

        Args:
            state: AgentState 对象

        Returns:
            RoundOutput 包含本轮所有交互数据
        """

        # 1. 叙事节拍
        beat = self.narrative_planner.get_current_beat(state.world.elapsed_minutes)
        phase = beat["phase"]

        # 2. 结局判断
        should_end, end_reason = self.ending_judge.should_end(
            state.world.elapsed_minutes, state.total_rounds, state.emotion
        )
        if should_end:
            return self._generate_ending(state, end_reason)

        # 3. 事件管理
        event_ended = False
        if not hasattr(state, 'event_round_count'):
            state.event_round_count = 0

        if state.event_round_count == 0 or self.event_manager.should_advance_event(state.event_round_count):
            # 事件结束或首次
            if state.event_round_count > 0:
                event_ended = True

            # 创建新事件
            event_type = self.event_manager.select_event(beat, state.used_event_ids, state.emotion)
            state.pending_event = {
                "type": event_type,
                "description": self.event_manager.get_event_description(event_type),
            }
            state.used_event_ids.add(event_type)
            state.event_round_count = 0

        # 4. 场景生成
        scene = self.scene_generator.select_scene(
            state.world.current_scene,
            state.pending_event.get("type", ""),
            state.world.elapsed_minutes
        )

        # 5. 台词生成（LLM）
        event_desc = state.pending_event.get("description", "角色与玩家互动")
        dialogue = await self.dialogue_generator.generate(state, event_desc)

        # 6. 选项生成（LLM + 规则）
        options = await self.option_generator.generate(state, dialogue)

        # 7. 更新事件轮次
        state.event_round_count += 1

        return RoundOutput(
            scene=scene,
            character_dialogue=dialogue,
            player_options=options,
            emotion_changes={},
            event_advance=event_ended,
            event_ended=event_ended,
            phase=phase,
            event_type=state.pending_event.get("type"),
            event_description=event_desc,
        )

    def apply_option_changes(self, state, option: Option) -> Dict[str, float]:
        """应用选项的数值变化（在玩家选择后调用）"""
        phase = self.narrative_planner.get_phase(state.world.elapsed_minutes)
        changes = self.emotion_calculator.calculate_changes(
            option, phase, state.character_personality
        )

        # 应用到情绪状态
        for key, delta in changes.items():
            if hasattr(state.emotion, key):
                current = getattr(state.emotion, key)
                setattr(state.emotion, key, max(0.0, min(100.0, current + delta)))

        return changes

    def _generate_ending(self, state, reason: str) -> RoundOutput:
        """生成结局"""
        ending_type = self.ending_judge.classify_ending(state.emotion)
        name = state.character_name or "角色"

        if ending_type == "happy_ending":
            dialogue = f"{name}: 谢谢你...我永远不会忘记今天的。"
        elif ending_type == "bad_ending":
            dialogue = f"{name}: ...（转身离去，没有回头）"
        elif ending_type == "neutral_ending":
            dialogue = f"{name}: 今天就这样吧。再见。"
        else:
            dialogue = f"{name}: 我们的故事...还没有结束。"

        return RoundOutput(
            scene=state.world.current_scene,
            character_dialogue=dialogue,
            player_options=[],
            emotion_changes={},
            event_advance=False,
            event_ended=False,
            phase="ending",
            is_game_finished=True,
            ending_type=ending_type,
            event_type="ending",
            event_description=f"故事结束：{ending_type}",
        )
