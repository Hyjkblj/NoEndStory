"""动态剧本系统

规则引擎控制 + AI 创作分离架构

组件：
- models: 数据结构定义
- rule_engine: 规则引擎（情绪计算、剧情推进、结局判定）
- script_manager: 剧本管理器（草案队列、叙事锚点、剪枝）
- ai_creator: AI 创作层（台词生成、选项生成）
- game_controller: 游戏控制器（主循环、状态管理）
"""
