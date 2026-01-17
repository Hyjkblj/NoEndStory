"""角色创建系统"""
import random
from database.db_manager import DatabaseManager
from data.character_attributes import CHARACTER_ATTRIBUTES


class CharacterCreator:
    """角色创建器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_character(self, name: str, gender: str, appearance: str, 
                        personality: str, scene_id: str = 'school') -> int:
        """创建角色
        
        Args:
            name: 角色名称
            gender: 性别（玩家选择）
            appearance: 外观描述（玩家选择）
            personality: 性格描述（玩家选择）
            scene_id: 场景ID
        
        Returns:
            角色ID
        """
        # 随机抽取决定因素
        random_attributes = {}
        for attr_type, options in CHARACTER_ATTRIBUTES.items():
            random_attributes[attr_type] = random.choice(options)
        
        # 创建角色
        character_id = self.db_manager.create_character(
            name=name,
            gender=gender,
            appearance=appearance,
            personality=personality,
            attributes=random_attributes,
            scene_id=scene_id
        )
        
        return character_id
    
    def get_character_info(self, character_id: int) -> dict:
        """获取角色完整信息"""
        character = self.db_manager.get_character(character_id)
        if not character:
            raise ValueError(f"角色 ID {character_id} 不存在")
        
        attributes = self.db_manager.get_character_attributes(character_id)
        states = self.db_manager.get_character_states(character_id)
        
        # 在会话关闭前获取所有属性值
        character_data = {
            'id': character.id,
            'name': character.name,
            'gender': character.gender,
            'appearance': character.appearance,
            'personality': character.personality,
            'scene_id': character.scene_id,
            'attributes': attributes,
            'states': {}
        }
        
        if states:
            character_data['states'] = {
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
        
        return character_data

