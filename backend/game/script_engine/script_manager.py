"""剧本管理器：草案队列、叙事锚点、开场事件池、剪枝"""
import random
from typing import Optional
from .models import (
    EventDraft, EventSummary, KeyBeat, OpeningEvent,
    NarrativeAnchor, AnchorPoint, EmotionState,
)
from utils.logger import get_logger

logger = get_logger(__name__)


# 默认开场事件池（当场景没有预设事件时使用）
DEFAULT_OPENING_EVENTS = [
    OpeningEvent(
        title="图书馆偶遇",
        description="你走进图书馆，发现 TA 正在角落看书。四目相对的瞬间，TA 微微一笑。",
        scene="library",
        mood="安静、温馨",
        option_directions=["坐到旁边一起看", "打个招呼就走", "假装没看见"],
    ),
    OpeningEvent(
        title="食堂拼桌",
        description="午餐时间食堂人满为患，TA 端着餐盘问你旁边有没有人。",
        scene="cafeteria",
        mood="轻松、日常",
        option_directions=["热情邀请坐下", "点点头让出位置", "冷漠地摇头"],
    ),
    OpeningEvent(
        title="课堂同桌",
        description="新学期的课堂上，TA 坐到了你旁边的空位上。",
        scene="classroom",
        mood="自然、好奇",
        option_directions=["主动打招呼", "默默观察", "低头假装在忙"],
    ),
    OpeningEvent(
        title="雨天共伞",
        description="放学时突然下起了雨，TA 站在教学楼门口没有带伞。",
        scene="school_gate",
        mood="意外、温暖",
        option_directions=["主动分享雨伞", "问 TA 要不要一起走", "假装没看到"],
    ),
    OpeningEvent(
        title="操场偶遇",
        description="傍晚的操场上，TA 一个人在跑步。你注意到 TA 已经跑了很久。",
        scene="playground",
        mood="轻松、运动",
        option_directions=["跟着跑过去", "在旁边等 TA 跑完", "默默走开"],
    ),
]


class ScriptManager:
    """剧本管理器"""

    def __init__(self):
        self.draft_queue: list[EventDraft] = []
        self.completed_events: list[EventSummary] = []
        self.narrative_anchor: Optional[NarrativeAnchor] = None

    def select_opening_event(
        self,
        scene_id: str,
        opening_events_pool: Optional[list[dict]] = None,
    ) -> OpeningEvent:
        """从场景事件池随机选取开场事件

        Args:
            scene_id: 场景 ID
            opening_events_pool: 场景的开场事件池（来自 data.scenes）
        """
        if opening_events_pool:
            selected = random.choice(opening_events_pool)
            return OpeningEvent(
                title=selected.get('title', '初遇'),
                description=selected.get('description', ''),
                scene=selected.get('scene', scene_id),
                mood=selected.get('mood', '自然'),
                option_directions=selected.get('option_directions', [
                    "积极回应", "保持中性", "消极回应"
                ]),
            )

        # 降级：使用默认事件池
        return random.choice(DEFAULT_OPENING_EVENTS)

    def initialize_script(
        self,
        scene_id: str,
        personality: list[str],
        initial_emotion: EmotionState,
    ) -> None:
        """初始化叙事锚点和事件 1-3 的简略草案"""
        # 生成叙事锚点
        self.narrative_anchor = self._generate_default_anchor(scene_id, personality)

        # 生成事件 1-3 简略草案
        beats = ['rising', 'rising', 'climax']
        for i, beat in enumerate(beats):
            draft = EventDraft(
                draft_id=f"event_{i + 1}",
                title=self._generate_default_title(i + 1, beat),
                scene=scene_id,
                narrative_beat=beat,
                brief_description=self._generate_default_brief(i + 1, beat),
                estimated_rounds=3 if beat != 'climax' else 4,
                detail_level="brief",
            )
            self.draft_queue.append(draft)

    def advance_script(self, summary: EventSummary) -> None:
        """事件结束后推进剧本"""
        self.completed_events.append(summary)

        # 移除已完成的草案
        if self.draft_queue:
            self.draft_queue.pop(0)

        # 升级下一个草案为完整版（标记需要升级）
        if self.draft_queue and self.draft_queue[0].detail_level == "brief":
            self.draft_queue[0].detail_level = "pending_upgrade"

        # 追加新的简略草案
        while len(self.draft_queue) < 4:
            idx = len(self.completed_events) + len(self.draft_queue)
            beat = self._get_beat_type(idx)
            draft = EventDraft(
                draft_id=f"event_{idx}",
                title=self._generate_default_title(idx, beat),
                scene=summary.scene,
                narrative_beat=beat,
                brief_description=self._generate_default_brief(idx, beat),
                estimated_rounds=3 if beat != 'climax' else 4,
                detail_level="brief",
            )
            self.draft_queue.append(draft)

    def get_anchor_progress(self) -> float:
        """计算锚点完成度"""
        if not self.narrative_anchor or not self.narrative_anchor.anchor_points:
            return 0.0

        achieved = sum(1 for a in self.narrative_anchor.anchor_points if a.is_achieved)
        return achieved / len(self.narrative_anchor.anchor_points)

    def check_anchor_achievement(self, emotion: EmotionState) -> None:
        """检查锚点是否达成"""
        if not self.narrative_anchor:
            return

        event_idx = len(self.completed_events)
        for anchor in self.narrative_anchor.anchor_points:
            if anchor.is_achieved:
                continue

            low, high = anchor.target_event_range
            if low <= event_idx <= high:
                # 检查情绪里程碑
                achieved = True
                for dim, condition in anchor.emotion_milestone.items():
                    if hasattr(emotion, dim):
                        val = getattr(emotion, dim)
                        if '>' in condition:
                            threshold = float(condition.replace('>', ''))
                            if val <= threshold:
                                achieved = False
                        elif '<' in condition:
                            threshold = float(condition.replace('<', ''))
                            if val >= threshold:
                                achieved = False
                anchor.is_achieved = achieved

    def _generate_default_anchor(
        self,
        scene_id: str,
        personality: list[str],
    ) -> NarrativeAnchor:
        """生成默认叙事锚点"""
        return NarrativeAnchor(
            theme="两个性格迥异的人从陌生到相知",
            emotional_arc="低开高走，中间有波折",
            total_events=5,
            anchor_points=[
                AnchorPoint(
                    anchor_id=0,
                    target_event_range=(0, 1),
                    narrative_goal="初次相遇，建立基本印象",
                    emotion_milestone={"favorability": ">40"},
                ),
                AnchorPoint(
                    anchor_id=1,
                    target_event_range=(1, 2),
                    narrative_goal="发现共同点，关系升温",
                    emotion_milestone={"favorability": ">55", "trust": ">45"},
                ),
                AnchorPoint(
                    anchor_id=2,
                    target_event_range=(2, 3),
                    narrative_goal="出现分歧或考验",
                    emotion_milestone={"hostility": ">20"},
                ),
                AnchorPoint(
                    anchor_id=3,
                    target_event_range=(3, 4),
                    narrative_goal="关系的最终定义",
                    emotion_milestone={},
                ),
            ],
        )

    def _get_beat_type(self, event_idx: int) -> str:
        """根据事件索引获取叙事阶段"""
        if event_idx <= 1:
            return 'rising'
        elif event_idx <= 3:
            return 'climax'
        else:
            return 'resolution'

    def _generate_default_title(self, idx: int, beat: str) -> str:
        titles = {
            'rising': ['日常相处', '渐渐熟悉', '深入了解'],
            'climax': ['信任考验', '矛盾爆发', '关键选择'],
            'resolution': ['和解', '告别', '约定'],
        }
        pool = titles.get(beat, ['继续'])
        return pool[idx % len(pool)]

    def _generate_default_brief(self, idx: int, beat: str) -> str:
        briefs = {
            'rising': '你们的关系在日常互动中逐渐升温。',
            'climax': '一个意外的事件打破了平静。',
            'resolution': '一切尘埃落定，关系迎来最终定义。',
        }
        return briefs.get(beat, '故事继续。')
