"""游戏服务"""
from typing import Dict, Any, Optional
import json
from api.services.game_session import GameSessionManager, GameSession
from api.services.character_service import CharacterService
from data.scenes import SCENES


class GameService:
    """游戏服务"""
    
    def __init__(self):
        self.session_manager = GameSessionManager()
        self.character_service = CharacterService()
    
    def init_game(
        self, 
        user_id: Optional[str], 
        character_id: Optional[int], 
        game_mode: str
    ) -> Dict[str, str]:
        """初始化游戏"""
        if not character_id:
            raise ValueError("character_id is required")
        
        # 创建游戏会话
        session = self.session_manager.create_session(
            user_id=user_id,
            character_id=character_id,
            game_mode=game_mode
        )
        
        return {
            'thread_id': session.thread_id,
            'user_id': session.user_id,
            'game_mode': session.game_mode
        }
    
    def initialize_story(self, thread_id: str, character_id: int) -> Dict[str, Any]:
        """初始化故事（触发初遇场景）"""
        session = self.session_manager.get_session(thread_id)
        if not session:
            raise ValueError(f"Thread {thread_id} not found")
        
        if session.character_id != character_id:
            raise ValueError("Character ID mismatch")
        
        # 获取开头事件
        scene_id = 'school'  # 默认场景
        event = session.story_engine.get_opening_event(
            character_id=character_id,
            scene_id=scene_id
        )
        
        session.is_initialized = True
        
        # 获取第一轮对话
        dialogue_data = session.story_engine.get_next_dialogue_round(character_id)
        session.current_dialogue_round = dialogue_data
        
        # 记录角色对话
        session.story_engine.record_character_dialogue(dialogue_data['character_dialogue'])
        
        return {
            'event_title': event.get('title', '初遇'),
            'story_background': event.get('story_background', ''),
            'scene': event.get('scene', scene_id),
            'character_dialogue': dialogue_data['character_dialogue'],
            'player_options': dialogue_data['player_options']
        }
    
    def process_input(
        self, 
        thread_id: str, 
        user_input: str, 
        option_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """处理玩家输入"""
        session = self.session_manager.get_session(thread_id)
        if not session:
            # 会话不存在，尝试从请求中获取character_id重新创建
            # 注意：这里需要前端传递character_id，或者从其他地方恢复
            raise ValueError(f"Thread {thread_id} not found. 会话可能已过期，请重新初始化游戏。")
        
        if not session.is_initialized:
            raise ValueError("Game not initialized. Call initialize_story first.")
        
        character_id = session.character_id
        
        # 如果提供了option_id，使用选项；否则使用user_input作为自由输入
        if option_id is not None and session.current_dialogue_round:
            # 从当前对话轮次中选择选项
            options = session.current_dialogue_round.get('player_options', [])
            if 0 <= option_id < len(options):
                selected_option = options[option_id]
                
                # 输出玩家选择
                option_text = selected_option.get('text', '') if isinstance(selected_option, dict) else str(selected_option)
                print(f"\n[玩家选择] 选项 {option_id + 1}: {option_text}")
                if isinstance(selected_option, dict) and selected_option.get('state_changes'):
                    print(f"  - 状态变化: {selected_option.get('state_changes')}")
                
                # 处理玩家选择
                session.story_engine.process_player_choice(
                    character_id=character_id,
                    choice=selected_option
                )
                
                # 保存对话轮次到向量数据库
                dialogue_round = len(session.story_engine.dialogue_history) // 2
                session.story_engine.save_dialogue_round_to_vector_db(
                    character_id=character_id,
                    dialogue_round=dialogue_round
                )
            else:
                # 无效的option_id，创建中性选项
                temp_option = {
                    'id': 2,
                    'text': user_input or "继续",
                    'type': 'neutral',
                    'state_changes': {}
                }
                session.story_engine.process_player_choice(
                    character_id=character_id,
                    choice=temp_option
                )
        else:
            # 自由输入（创建中性选项）
            print(f"\n[玩家输入] 自由文本: {user_input}")
            
            temp_option = {
                'id': 2,
                'text': user_input or "继续",
                'type': 'neutral',
                'state_changes': {}
            }
            session.story_engine.process_player_choice(
                character_id=character_id,
                choice=temp_option
            )
        
        # 检查是否应该继续当前事件的对话
        should_continue = session.story_engine.should_continue_dialogue()
        
        response_data = {
            'character_dialogue': None,
            'player_options': None,
            'story_background': None,
            'event_title': None,
            'scene': None,
            'is_event_finished': False,
            'is_game_finished': False
        }
        
        if should_continue:
            # 继续当前事件的对话
            dialogue_data = session.story_engine.get_next_dialogue_round(character_id)
            session.current_dialogue_round = dialogue_data
            session.story_engine.record_character_dialogue(dialogue_data['character_dialogue'])
            
            # 输出详细信息到控制台
            self._print_dialogue_info(character_id, session.story_engine.current_event, dialogue_data)
            
            response_data.update({
                'character_dialogue': dialogue_data['character_dialogue'],
                'player_options': dialogue_data['player_options'],
                'story_background': session.story_engine.current_event.get('story_background') if session.story_engine.current_event else None,
                'event_title': session.story_engine.current_event.get('title') if session.story_engine.current_event else None,
                'scene': session.story_engine.current_event.get('scene') if session.story_engine.current_event else None,
            })
        else:
            # 当前事件对话结束，保存事件并进入下一个事件
            session.story_engine.save_event_to_vector_db(character_id)
            
            # 检查游戏是否结束
            if session.story_engine.is_game_finished():
                # 获取结尾事件
                ending_event = session.story_engine.get_ending_event(character_id)
                dialogue_data = session.story_engine.get_next_dialogue_round(character_id)
                session.current_dialogue_round = dialogue_data
                session.story_engine.record_character_dialogue(dialogue_data['character_dialogue'])
                
                # 输出详细信息到控制台
                self._print_dialogue_info(character_id, ending_event, dialogue_data)
                
                response_data.update({
                    'character_dialogue': dialogue_data['character_dialogue'],
                    'player_options': dialogue_data['player_options'],
                    'story_background': ending_event.get('story_background'),
                    'event_title': ending_event.get('title', '结局'),
                    'scene': ending_event.get('scene'),
                    'is_game_finished': True
                })
            else:
                # 获取下一个事件
                next_event = session.story_engine.get_next_event(character_id)
                dialogue_data = session.story_engine.get_next_dialogue_round(character_id)
                session.current_dialogue_round = dialogue_data
                session.story_engine.record_character_dialogue(dialogue_data['character_dialogue'])
                
                # 输出详细信息到控制台
                self._print_dialogue_info(character_id, next_event, dialogue_data)
                
                response_data.update({
                    'character_dialogue': dialogue_data['character_dialogue'],
                    'player_options': dialogue_data['player_options'],
                    'story_background': next_event.get('story_background'),
                    'event_title': next_event.get('title'),
                    'scene': next_event.get('scene'),
                    'is_event_finished': True
                })
        
        return response_data
    
    def _print_dialogue_info(self, character_id: int, event: Dict, dialogue_data: Dict):
        """输出详细的对话信息到控制台"""
        try:
            # 获取角色信息
            character = self.character_service.db_manager.get_character(character_id)
            attributes = self.character_service.db_manager.get_character_attributes(character_id)
            states = self.character_service.db_manager.get_character_states(character_id)
            
            print("\n" + "="*80)
            print("【游戏对话信息】")
            print("="*80)
            
            # 场景信息
            scene = event.get('scene', '未知场景')
            event_title = event.get('title', '未知事件')
            story_background = event.get('story_background', '')
            
            print(f"\n📍 【场景】: {scene}")
            print(f"📖 【事件】: {event_title}")
            if story_background:
                print(f"📝 【故事背景】: {story_background[:200]}{'...' if len(story_background) > 200 else ''}")
            
            # 角色设定
            if character:
                print(f"\n👤 【角色设定】")
                print(f"   姓名: {character.name}")
                print(f"   性别: {character.gender}")
                print(f"   外观: {character.appearance[:100]}{'...' if len(character.appearance) > 100 else ''}")
                print(f"   性格: {character.personality[:100]}{'...' if len(character.personality) > 100 else ''}")
                
                # 详细属性
                if attributes:
                    print(f"   详细属性:")
                    if hasattr(attributes, 'appearance_data') and attributes.appearance_data:
                        try:
                            app_data = json.loads(attributes.appearance_data) if isinstance(attributes.appearance_data, str) else attributes.appearance_data
                            if isinstance(app_data, dict):
                                if 'keywords' in app_data:
                                    print(f"      - 外观关键词: {', '.join(app_data['keywords']) if isinstance(app_data['keywords'], list) else app_data['keywords']}")
                                if 'height' in app_data:
                                    print(f"      - 身高: {app_data['height']}")
                                if 'weight' in app_data:
                                    print(f"      - 体重: {app_data['weight']}")
                        except:
                            pass
                    
                    if hasattr(attributes, 'personality_data') and attributes.personality_data:
                        try:
                            pers_data = json.loads(attributes.personality_data) if isinstance(attributes.personality_data, str) else attributes.personality_data
                            if isinstance(pers_data, dict) and 'keywords' in pers_data:
                                print(f"      - 性格关键词: {', '.join(pers_data['keywords']) if isinstance(pers_data['keywords'], list) else pers_data['keywords']}")
                        except:
                            pass
                    
                    if hasattr(attributes, 'age') and attributes.age:
                        print(f"      - 年龄: {attributes.age}")
            
            # 角色当前状态
            if states:
                print(f"\n💭 【角色当前状态】")
                print(f"   好感度: {states.favorability}/100")
                print(f"   信任度: {states.trust}/100")
                print(f"   敌意值: {states.hostility}/100")
                print(f"   依赖度: {states.dependence}/100")
                print(f"   情绪值: {states.emotion}/100")
                print(f"   压力值: {states.stress}/100")
                print(f"   焦虑值: {states.anxiety}/100")
                print(f"   快乐值: {states.happiness}/100")
                print(f"   悲伤值: {states.sadness}/100")
                print(f"   自信值: {states.confidence}/100")
                print(f"   主动性: {states.initiative}/100")
                print(f"   谨慎度: {states.caution}/100")
            
            # 对话内容
            character_dialogue = dialogue_data.get('character_dialogue', '')
            player_options = dialogue_data.get('player_options', [])
            
            print(f"\n💬 【角色对话】")
            print(f"   {character_dialogue}")
            
            if player_options:
                print(f"\n🎮 【玩家选项】")
                for idx, option in enumerate(player_options, 1):
                    option_text = option.get('text', '') if isinstance(option, dict) else str(option)
                    print(f"   {idx}. {option_text}")
            
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"[警告] 输出对话信息时出错: {e}")
    
    def check_ending(self, thread_id: str) -> Dict[str, Any]:
        """检查是否满足结局条件"""
        session = self.session_manager.get_session(thread_id)
        if not session:
            raise ValueError(f"Thread {thread_id} not found")
        
        is_finished = session.story_engine.is_game_finished()
        
        if is_finished:
            # 获取角色状态值
            states = session.db_manager.get_character_states(session.character_id)
            if states:
                favorability = states.favorability
                trust = states.trust
                hostility = states.hostility
                
                # 确定结局类型
                if favorability > 60 and trust > 50:
                    ending_type = "good_ending"
                    ending_desc = "经过一系列事件，你们的关系变得更加亲密，这是一个美好的结局。"
                elif favorability < 30 or hostility > 50:
                    ending_type = "bad_ending"
                    ending_desc = "关系走向了不好的方向，你们之间的距离越来越远。"
                elif trust > 50 and favorability > 40:
                    ending_type = "neutral_ending"
                    ending_desc = "你们的关系保持在一个稳定的状态，未来还有无限可能。"
                else:
                    ending_type = "open_ending"
                    ending_desc = "故事还在继续，结局尚未确定..."
                
                return {
                    'has_ending': True,
                    'ending': {
                        'type': ending_type,
                        'description': ending_desc,
                        'favorability': favorability,
                        'trust': trust,
                        'hostility': hostility
                    }
                }
        
        return {
            'has_ending': False,
            'ending': None
        }
    
    def trigger_ending(self, thread_id: str) -> Dict[str, Any]:
        """触发结局"""
        session = self.session_manager.get_session(thread_id)
        if not session:
            raise ValueError(f"Thread {thread_id} not found")
        
        character_id = session.character_id
        
        # 获取结尾事件
        ending_event = session.story_engine.get_ending_event(character_id)
        
        # 获取第一轮对话
        dialogue_data = session.story_engine.get_next_dialogue_round(character_id)
        session.current_dialogue_round = dialogue_data
        session.story_engine.record_character_dialogue(dialogue_data['character_dialogue'])
        
        return {
            'event_title': ending_event.get('title', '结局'),
            'story_background': ending_event.get('story_background', ''),
            'scene': ending_event.get('scene'),
            'ending_type': ending_event.get('ending_type'),
            'character_dialogue': dialogue_data['character_dialogue'],
            'player_options': dialogue_data['player_options']
        }

