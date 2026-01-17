"""角色服务"""
from typing import Dict, Any
from database.db_manager import DatabaseManager
from game.character_creator import CharacterCreator
from data.player_choices import GENDER_OPTIONS, APPEARANCE_OPTIONS, PERSONALITY_OPTIONS
import random


class CharacterService:
    """角色服务"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.character_creator = CharacterCreator(self.db_manager)
    
    def _parse_character_data(self, request_data: Dict[str, Any]) -> Dict[str, str]:
        """解析前端发送的JSON数据，生成完整的人物设定描述
        
        Args:
            request_data: 创建角色请求数据
            
        Returns:
            包含解析后数据的字典
        """
        name = request_data.get('name', '未命名角色')
        
        # 解析性别
        gender = request_data.get('gender', '')
        if gender == 'male':
            gender_str = '男'
        elif gender == 'female':
            gender_str = '女'
        else:
            gender_str = random.choice(GENDER_OPTIONS)
        
        # 解析外观数据
        appearance = request_data.get('appearance', {})
        appearance_parts = []
        
        if isinstance(appearance, dict):
            # 提取关键词
            keywords = appearance.get('keywords', [])
            if isinstance(keywords, list) and len(keywords) > 0:
                appearance_parts.extend(keywords)
            
            # 提取身高
            height = appearance.get('height')
            if height:
                appearance_parts.append(f'身高{height}cm')
            
            # 提取体重
            weight = appearance.get('weight')
            if weight:
                appearance_parts.append(f'体重{weight}kg')
            
            # 如果有description字段，也加入
            description = appearance.get('description')
            if description:
                appearance_parts.append(description)
        
        # 如果没有外观数据，使用默认值
        if not appearance_parts:
            appearance_parts = [random.choice(APPEARANCE_OPTIONS)]
        
        appearance_str = '，'.join(appearance_parts) if appearance_parts else random.choice(APPEARANCE_OPTIONS)
        
        # 解析性格数据
        personality = request_data.get('personality', {})
        personality_parts = []
        
        if isinstance(personality, dict):
            # 提取关键词
            keywords = personality.get('keywords', [])
            if isinstance(keywords, list) and len(keywords) > 0:
                personality_parts.extend(keywords)
            
            # 如果有traits字段
            traits = personality.get('traits', [])
            if isinstance(traits, list) and len(traits) > 0:
                personality_parts.extend(traits)
        
        # 如果没有性格数据，使用默认值
        if not personality_parts:
            personality_parts = [random.choice(PERSONALITY_OPTIONS)]
        
        personality_str = '，'.join(personality_parts) if personality_parts else random.choice(PERSONALITY_OPTIONS)
        
        # 解析背景数据
        background = request_data.get('background', {})
        background_str = ''
        
        if isinstance(background, dict):
            style = background.get('style')
            if style:
                background_str = f'风格：{style}'
        
        # 解析年龄
        age = request_data.get('age')
        age_str = f'{age}岁' if age else ''
        
        # 生成完整的人物设定描述（用于AI prompt）
        character_prompt_parts = [
            f'姓名：{name}',
            f'性别：{gender_str}',
        ]
        
        if age_str:
            character_prompt_parts.append(age_str)
        
        character_prompt_parts.extend([
            f'外观：{appearance_str}',
            f'性格：{personality_str}',
        ])
        
        if background_str:
            character_prompt_parts.append(background_str)
        
        character_prompt = '；'.join(character_prompt_parts)
        
        return {
            'name': name,
            'gender': gender_str,
            'appearance': appearance_str,
            'personality': personality_str,
            'background': background_str,
            'age': age_str,
            'character_prompt': character_prompt  # 完整的人物设定prompt
        }
    
    def create_character(self, request_data: Dict[str, Any]) -> int:
        """创建角色
        
        Args:
            request_data: 创建角色请求数据
            
        Returns:
            角色ID
        """
        # 解析前端发送的JSON数据
        parsed_data = self._parse_character_data(request_data)
        
        scene_id = request_data.get('initial_scene', 'school')
        
        # 保存原始结构化数据到character_attributes表（用于后续返回）
        appearance_data = request_data.get('appearance', {})
        personality_data = request_data.get('personality', {})
        background_data = request_data.get('background', {})
        age = request_data.get('age')
        gender_raw = request_data.get('gender', '')
        
        # 创建角色（使用解析后的数据用于AI生成）
        character_id = self.character_creator.create_character(
            name=parsed_data['name'],
            gender=parsed_data['gender'],
            appearance=parsed_data['appearance'],
            personality=parsed_data['personality'],
            scene_id=scene_id
        )
        
        # 保存结构化数据到character_attributes表
        import json
        from models.character import CharacterAttribute
        
        with self.db_manager.get_session() as session:
            # 保存年龄
            if age is not None:
                attr = CharacterAttribute(
                    character_id=character_id,
                    attribute_type='age',
                    attribute_value=str(age)
                )
                session.add(attr)
            
            # 保存原始性别（用于返回）
            if gender_raw:
                attr = CharacterAttribute(
                    character_id=character_id,
                    attribute_type='gender_raw',
                    attribute_value=gender_raw
                )
                session.add(attr)
            
            # 保存结构化外观数据
            if appearance_data:
                attr = CharacterAttribute(
                    character_id=character_id,
                    attribute_type='appearance_data',
                    attribute_value=json.dumps(appearance_data, ensure_ascii=False)
                )
                session.add(attr)
            
            # 保存结构化性格数据
            if personality_data:
                attr = CharacterAttribute(
                    character_id=character_id,
                    attribute_type='personality_data',
                    attribute_value=json.dumps(personality_data, ensure_ascii=False)
                )
                session.add(attr)
            
            # 保存结构化背景数据
            if background_data:
                attr = CharacterAttribute(
                    character_id=character_id,
                    attribute_type='background_data',
                    attribute_value=json.dumps(background_data, ensure_ascii=False)
                )
                session.add(attr)
        
        return character_id
    
    def get_character(self, character_id: int) -> Dict[str, Any]:
        """获取角色信息（返回结构化数据）"""
        character_info = self.character_creator.get_character_info(character_id)
        attributes = character_info.get('attributes', {})
        
        # 从attributes中提取结构化数据
        import json
        
        # 提取年龄
        age = None
        if 'age' in attributes:
            try:
                age = int(attributes['age'])
            except:
                pass
        
        # 提取原始性别
        gender_raw = attributes.get('gender_raw', '')
        if not gender_raw:
            # 如果没有保存原始性别，从character表转换
            gender_db = character_info.get('gender', '')
            if gender_db == '男':
                gender_raw = 'male'
            elif gender_db == '女':
                gender_raw = 'female'
        
        # 提取结构化外观数据
        appearance_data = {}
        if 'appearance_data' in attributes:
            try:
                appearance_data = json.loads(attributes['appearance_data'])
            except:
                pass
        
        # 如果没有结构化数据，从原始数据重建
        if not appearance_data:
            appearance_data = {
                'keywords': character_info['appearance'].split('，') if '，' in character_info['appearance'] else [character_info['appearance']],
            }
            # 尝试从appearance字符串中提取height和weight
            appearance_str = character_info['appearance']
            import re
            height_match = re.search(r'身高(\d+)cm', appearance_str)
            weight_match = re.search(r'体重(\d+)kg', appearance_str)
            if height_match:
                appearance_data['height'] = int(height_match.group(1))
            if weight_match:
                appearance_data['weight'] = int(weight_match.group(1))
        
        # 提取结构化性格数据
        personality_data = {}
        if 'personality_data' in attributes:
            try:
                personality_data = json.loads(attributes['personality_data'])
            except:
                pass
        
        # 如果没有结构化数据，从原始数据重建
        if not personality_data:
            personality_data = {
                'keywords': character_info['personality'].split('，') if '，' in character_info['personality'] else [character_info['personality']],
            }
        
        # 提取结构化背景数据
        background_data = {}
        if 'background_data' in attributes:
            try:
                background_data = json.loads(attributes['background_data'])
            except:
                pass
        
        # 转换为API响应格式（保持结构化）
        return {
            'character_id': str(character_info['id']),
            'name': character_info['name'],
            'height': appearance_data.get('height'),
            'weight': appearance_data.get('weight'),
            'age': age,
            'gender': gender_raw or (character_info['gender'] if character_info['gender'] in ['male', 'female'] else None),
            'appearance': {
                'keywords': appearance_data.get('keywords', []),
                'height': appearance_data.get('height'),
                'weight': appearance_data.get('weight'),
            },
            'personality': {
                'keywords': personality_data.get('keywords', []),
            },
            'background': background_data,
            'identity': character_info.get('scene_id', 'school'),
            'initial_scene': character_info.get('scene_id', 'school')
        }
    
    def get_character_images(self, character_id: int) -> list:
        """获取角色图片列表（当前返回空列表）"""
        # TODO: 实现图片获取逻辑
        return []

