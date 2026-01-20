"""事件生成器"""
import random
from typing import Dict, List
from database.vector_db import VectorDatabase
from database.db_manager import DatabaseManager
from game.ai_generator import AIGenerator


class EventGenerator:
    """事件生成器"""
    
    def __init__(self, vector_db: VectorDatabase, db_manager: DatabaseManager):
        self.vector_db = vector_db
        self.db_manager = db_manager
        self.ai_generator = AIGenerator()
    
    def generate_story_background(self, character_id: int, event_context: str, 
                                  previous_contexts: List[str] = None) -> str:
        """生成故事背景文本（使用AI，基于向量数据库检索的历史事件，避免重复，确保连续性）"""
        # 从向量数据库检索相似的历史事件（使用更广泛的查询）
        results = self.vector_db.search_similar_events(
            character_id=character_id,
            query=event_context,
            n_results=5  # 增加检索数量，更好地避免重复
        )
        
        # 提取历史事件文本
        previous_events = []
        if results.get('documents') and len(results['documents']) > 0:
            previous_events = results['documents']
        
        # 如果提供了之前的事件上下文，也加入避免重复的检查
        if previous_contexts:
            # 将之前的事件上下文也传递给AI，帮助避免重复
            context_summary = "\n已发生的事件摘要（不要重复）：\n" + "\n".join([f"- {ctx}" for ctx in previous_contexts[-5:]])
            if context_summary:
                event_context = f"{event_context}\n\n{context_summary}"
        
        # 获取角色名称
        character = self.db_manager.get_character(character_id)
        character_name = character.name if character else "角色"
        
        # 使用AI生成故事背景（必须基于向量数据库检索的历史事件）
        return self.ai_generator.generate_story_background(
            character_id=character_id,
            previous_events=previous_events,  # 从向量数据库检索的历史事件
            current_context=event_context,
            character_name=character_name
        )
    
    def generate_character_dialogue(self, character_id: int, story_background: str, 
                                   dialogue_round: int = 1, previous_dialogues: List[str] = None) -> str:
        """生成角色对话文本（使用AI，基于故事背景、角色决定因素和状态值）
        
        Args:
            character_id: 角色ID
            story_background: 故事背景
            dialogue_round: 对话轮次
            previous_dialogues: 之前的完整对话历史
        """
        character = self.db_manager.get_character(character_id)
        attributes = self.db_manager.get_character_attributes(character_id)
        states = self.db_manager.get_character_states(character_id)
        
        if not character or not states:
            return "角色说道：\"...\""
        
        # 构建角色信息字典
        character_info = {
            'personality': character.personality,
            'gender': character.gender,
            'appearance': character.appearance,
            'attributes': attributes
        }
        
        # 构建状态值字典
        state_values = {
            'favorability': states.favorability,
            'trust': states.trust,
            'hostility': states.hostility,
            'dependence': states.dependence,
            'emotion': states.emotion,
            'stress': states.stress,
            'anxiety': states.anxiety,
            'happiness': states.happiness,
            'sadness': states.sadness,
            'confidence': states.confidence,
            'initiative': states.initiative,
            'caution': states.caution
        }
        
        # 输出生成对话前的信息
        print(f"\n[AI生成] 正在生成角色对话 (轮次: {dialogue_round})")
        print(f"  - 角色: {character.name if character else '未知'}")
        print(f"  - 当前状态: 好感度={state_values.get('favorability', 0)}, 信任度={state_values.get('trust', 0)}, 情绪={state_values.get('emotion', 0)}")
        print(f"  - 故事背景: {story_background[:100]}{'...' if len(story_background) > 100 else ''}")
        
        # 使用AI生成对话（传递之前的对话历史，必须基于向量数据库检索）
        dialogue = self.ai_generator.generate_character_dialogue(
            story_background=story_background,
            character_info=character_info,
            state_values=state_values,
            dialogue_round=dialogue_round,
            previous_dialogues=previous_dialogues or [],  # 包含从向量数据库检索的历史对话
            character_name=character.name if character else "角色"
        )
        
        print(f"[AI生成] 对话生成完成: {dialogue[:80]}{'...' if len(dialogue) > 80 else ''}\n")
        
        return dialogue
    
    def generate_player_options(self, story_background: str, character_dialogue: str,
                                dialogue_round: int, previous_dialogues: List[str] = None) -> List[Dict]:
        """生成玩家选项（使用AI，生成对话内容而非简单选择）
        
        Args:
            story_background: 故事背景
            character_dialogue: 角色刚才说的话
            dialogue_round: 对话轮次
            previous_dialogues: 之前的完整对话历史
        """
        return self.ai_generator.generate_player_options(
            story_background=story_background,
            character_dialogue=character_dialogue,
            dialogue_round=dialogue_round,
            previous_dialogues=previous_dialogues or []
        )
    
    def generate_event(self, character_id: int, event_id: str, 
                      event_context: str, previous_contexts: List[str] = None) -> Dict:
        """生成完整事件（包含故事背景）
        
        Args:
            character_id: 角色ID
            event_id: 事件ID
            event_context: 事件上下文
            previous_contexts: 之前的事件上下文列表（用于避免重复）
        """
        # 生成故事背景文本（传递之前的事件上下文，避免重复）
        story_background = self.generate_story_background(
            character_id, 
            event_context,
            previous_contexts=previous_contexts
        )
        
        return {
            'event_id': event_id,
            'story_background': story_background,
            'event_context': event_context
        }
    
    def generate_dialogue_round(self, character_id: int, story_background: str,
                                dialogue_round: int, previous_dialogues: List[str] = None) -> Dict:
        """生成一轮对话（角色对话 + 玩家选项）
        
        Args:
            character_id: 角色ID
            story_background: 故事背景
            dialogue_round: 对话轮次
            previous_dialogues: 之前的完整对话历史（包含角色对话和玩家选择）
        """
        # 生成角色对话（考虑之前的对话历史）
        character_dialogue = self.generate_character_dialogue(
            character_id=character_id,
            story_background=story_background,
            dialogue_round=dialogue_round,
            previous_dialogues=previous_dialogues or []
        )
        
        # 生成玩家选项（考虑之前的对话历史）
        player_options = self.generate_player_options(
            story_background=story_background,
            character_dialogue=character_dialogue,
            dialogue_round=dialogue_round,
            previous_dialogues=previous_dialogues or []
        )
        
        return {
            'character_dialogue': character_dialogue,
            'player_options': player_options
        }

