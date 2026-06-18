"""ConsistencyAgent — 质量门

职责：
  - 规则检查（快速，每轮必做）
  - 可选 LLM 检查（慢速，关键轮次做）

规则检查：
  ✅ 情绪突变（|delta| > 30）
  ✅ 对话过短（len < 5）
  ✅ 对话重复（unique_chars / total_chars < 0.3）
  ✅ 事件连续重复

LLM 检查（可选）：
  ✅ 台词是否符合角色性格
  ✅ 台词是否与当前情绪一致
"""
from typing import Dict, Any, List
from utils.logger import get_logger

logger = get_logger("consistency_agent")


class ConsistencyAgent:
    """一致性 Agent — 输出校验"""

    MAX_EMOTION_DELTA = 30.0

    def __init__(self, llm_tool=None):
        self.llm = llm_tool

    async def check(self, state, dialogue: str, emotion_changes: dict) -> Dict[str, Any]:
        """校验输出

        Args:
            state: AgentState 对象
            dialogue: 生成的台词
            emotion_changes: 情绪变化量

        Returns:
            {"passed": bool, "violations": list, "severity": str}
        """
        violations = []

        # 1. 规则检查（必做）
        violations.extend(self._rule_checks(state, dialogue, emotion_changes))

        # 2. LLM 检查（可选，每 5 轮做一次）
        if self.llm and state.total_rounds % 5 == 0:
            llm_violations = await self._llm_checks(state, dialogue)
            violations.extend(llm_violations)

        severity = "error" if len(violations) >= 3 else ("warning" if violations else "ok")

        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "severity": severity,
        }

    def _rule_checks(self, state, dialogue: str, emotion_changes: dict) -> List[str]:
        """规则检查"""
        violations = []

        # 情绪突变
        for key, delta in emotion_changes.items():
            if abs(delta) > self.MAX_EMOTION_DELTA:
                violations.append(f"情绪[{key}]变化过大: {delta:.1f}")

        # 对话过短
        if dialogue and len(dialogue.strip()) < 5:
            violations.append("对话内容过短")

        # 对话重复
        if dialogue and self._is_repetitive(dialogue):
            violations.append("对话内容重复度过高")

        # 事件连续重复
        if len(state.event_history) >= 2:
            last = state.event_history[-1]
            current_type = state.pending_event.get("type") if state.pending_event else None
            if current_type and last.get("type") == current_type:
                violations.append(f"连续重复事件: {current_type}")

        return violations

    async def _llm_checks(self, state, dialogue: str) -> List[str]:
        """LLM 语义检查"""
        violations = []

        try:
            personality = state.character_personality.get("keywords", [])
            prompt = f"""检查以下对话是否符合角色性格。

角色性格：{'、'.join(personality) if personality else '普通'}
角色台词：{dialogue}
当前情绪：好感度{state.emotion.favorability:.0f}，快乐{state.emotion.happiness:.0f}

如果有问题，返回具体问题。如果没有问题，返回"无问题"。"""

            result = await self.llm.generate(
                prompt, max_tokens=100, temperature=0.3, call_type="dialogue"
            )

            if result and "无问题" not in result and len(result) > 5:
                violations.append(f"LLM 检查: {result[:50]}")

        except Exception as e:
            logger.warning(f"LLM 检查失败: {e}")

        return violations

    def _is_repetitive(self, text: str) -> bool:
        """检测文本重复度"""
        if len(text) < 10:
            return False
        unique = len(set(text))
        return unique / len(text) < 0.3
