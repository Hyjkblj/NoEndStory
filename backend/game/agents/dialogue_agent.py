"""Dialogue Agent — 调用 LLM 生成角色台词"""
from typing import Dict, Any, Optional
from .base import BaseAgent
from .state import AgentState


class DialogueAgent(BaseAgent):
    """对话Agent：生成角色台词和玩家选项"""

    def __init__(self, text_gen=None):
        super().__init__("dialogue")
        self.text_gen = text_gen  # TextGenerationService

    async def think(self, state: AgentState) -> Dict[str, Any]:
        if not self.text_gen or not self.text_gen.enabled:
            return {
                "character_dialogue": self._fallback_dialogue(state),
                "player_options": self._fallback_options(),
            }

        # 构建对话 prompt
        prompt = self._build_dialogue_prompt(state)
        dialogue = self._generate_dialogue(prompt)
        options = self._generate_options(state, dialogue)

        state.output_dialogue = dialogue
        state.output_options = options

        return {
            "character_dialogue": dialogue,
            "player_options": options,
        }

    def _build_dialogue_prompt(self, state: AgentState) -> str:
        """构建角色对话 prompt"""
        emotion = state.emotion
        world = state.world
        event = state.pending_event or {}

        context_parts = [
            f"你是一个AI角色，名叫{state.character_name}。",
            f"当前场景：{world.current_scene}，时间：{world.current_time}，天气：{world.weather}。",
            f"当前剧情阶段：{state.phase.value if state.phase else 'opening'}。",
            f"当前事件：{event.get('description', '与玩家互动')}。",
            "",
            "角色当前情绪状态：",
            f"- 好感度：{emotion.favorability:.0f}/100",
            f"- 信任度：{emotion.trust:.0f}/100",
            f"- 情绪：{emotion.emotion:.0f}/100",
            f"- 快乐：{emotion.happiness:.0f}/100",
            f"- 压力：{emotion.stress:.0f}/100",
            f"- 自信：{emotion.confidence:.0f}/100",
            "",
            "请根据以上状态，以角色的口吻回复一句话（20-80字），",
            "回复要符合当前的情绪状态和剧情阶段。",
            f"直接返回角色台词，格式：{state.character_name}: [台词内容]",
        ]

        return "\n".join(context_parts)

    def _generate_dialogue(self, prompt: str) -> str:
        """调用 LLM 生成对话"""
        try:
            result = self.text_gen._call_text_generation(
                prompt, max_tokens=100, temperature=0.9, call_type="dialogue"
            )
            return result.strip() if result else ""
        except Exception:
            return ""

    def _generate_options(self, state: AgentState, dialogue: str) -> list:
        """生成3个玩家选项"""
        return [
            {"id": 1, "text": "积极回应", "type": "positive"},
            {"id": 2, "text": "保持距离", "type": "neutral"},
            {"id": 3, "text": "追问更多", "type": "curious"},
        ]

    def _fallback_dialogue(self, state: AgentState) -> str:
        name = state.character_name or "角色"
        return f"{name}: 嗯...（看起来有些犹豫）"

    def _fallback_options(self) -> list:
        return [
            {"id": 1, "text": "积极回应", "type": "positive"},
            {"id": 2, "text": "保持距离", "type": "neutral"},
            {"id": 3, "text": "追问更多", "type": "curious"},
        ]
