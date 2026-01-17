"""剧情推进引擎"""
import random
from typing import Dict, List
from data.scenes import SCENES, SCENE_DERIVATIONS
from game.event_generator import EventGenerator
from database.db_manager import DatabaseManager
import config


class StoryEngine:
    """剧情推进引擎"""
    
    def __init__(self, event_generator: EventGenerator, db_manager: DatabaseManager):
        self.event_generator = event_generator
        self.db_manager = db_manager
        self.current_event_count = 0
        self.current_event = None  # 当前事件信息
        self.dialogue_history = []  # 当前事件的完整对话历史（包含角色对话和玩家选择）
        self.min_dialogue_rounds = 4  # 最少对话轮数
        self.current_scene = 'school'  # 当前场景
        self.previous_event_contexts = []  # 记录之前的事件上下文，避免重复
    
    def get_opening_event(self, character_id: int, scene_id: str = 'school') -> Dict:
        """获取开头事件（随机抽取）"""
        scene = SCENES.get(scene_id)
        if not scene:
            raise ValueError(f"场景 {scene_id} 不存在")
        
        opening_events = scene['opening_events']
        selected_event = random.choice(opening_events)
        
        # 生成事件（包含故事背景）
        event = self.event_generator.generate_event(
            character_id=character_id,
            event_id=selected_event['id'],
            event_context=selected_event['description'],
            previous_contexts=self.previous_event_contexts
        )
        
        event['title'] = selected_event['title']
        event['event_context'] = selected_event['description']
        self.current_event_count = 1
        self.current_event = event
        self.dialogue_history = []  # 重置对话历史
        
        return event
    
    def get_middle_event(self, character_id: int, event_number: int) -> Dict:
        """获取中间事件（基于历史事件推演，避免重复，支持场景切换）"""
        # 从向量数据库获取历史事件，用于生成新事件上下文
        # 使用更广泛的查询，获取更多历史事件
        previous_events = self.event_generator.vector_db.search_similar_events(
            character_id=character_id,
            query="剧情发展 事件 场景",
            n_results=5
        )
        
        # 获取当前场景和可能的衍生场景
        possible_scenes = SCENE_DERIVATIONS.get(self.current_scene, [self.current_scene])
        
        # 智能选择下一个场景：
        # 1. 如果当前场景有衍生场景，优先选择未使用过的衍生场景
        # 2. 如果所有衍生场景都用过，可以回到原场景或选择其他场景
        # 3. 基于剧情逻辑，可以随机选择，但要有一定概率切换场景
        if len(possible_scenes) > 1:
            # 70%概率切换场景，30%概率保持当前场景
            if random.random() < 0.7:
                # 排除当前场景，从衍生场景中选择
                available_scenes = [s for s in possible_scenes if s != self.current_scene]
                if available_scenes:
                    next_scene = random.choice(available_scenes)
                else:
                    next_scene = self.current_scene
            else:
                next_scene = self.current_scene
        else:
            next_scene = self.current_scene
        
        # 生成事件上下文（由AI基于历史事件生成，确保不重复且有连续性）
        event_context = self._generate_event_context(
            character_id=character_id,
            event_number=event_number,
            previous_events=previous_events.get('documents', []),
            current_scene=next_scene
        )
        
        # 更新当前场景
        if next_scene != self.current_scene:
            scene_name = SCENES.get(next_scene, {}).get('name', next_scene)
            print(f"[场景切换] 从 {SCENES.get(self.current_scene, {}).get('name', self.current_scene)} 切换到 {scene_name}")
            self.current_scene = next_scene
        
        event_id = f"middle_event_{event_number}"
        
        event = self.event_generator.generate_event(
            character_id=character_id,
            event_id=event_id,
            event_context=event_context,
            previous_contexts=self.previous_event_contexts
        )
        
        event['title'] = f"事件 {event_number}"
        event['event_context'] = event_context
        event['scene'] = self.current_scene
        self.current_event_count = event_number + 1
        self.current_event = event
        self.dialogue_history = []  # 重置对话历史
        # 记录事件上下文摘要，避免重复（记录更长的摘要）
        self.previous_event_contexts.append(event_context[:150])
        # 只保留最近10个事件上下文，避免列表过长
        if len(self.previous_event_contexts) > 10:
            self.previous_event_contexts = self.previous_event_contexts[-10:]
        
        # 输出新事件信息
        scene_name = SCENES.get(self.current_scene, {}).get('name', self.current_scene)
        print(f"\n[新事件] 事件 {event_number} 开始")
        print(f"  - 场景: {scene_name} ({self.current_scene})")
        print(f"  - 事件上下文: {event_context[:150]}{'...' if len(event_context) > 150 else ''}")
        if event.get('story_background'):
            print(f"  - 故事背景: {event.get('story_background')[:150]}{'...' if len(event.get('story_background', '')) > 150 else ''}\n")
        
        return event
    
    def _generate_event_context(self, character_id: int, event_number: int, 
                                previous_events: List[str], current_scene: str) -> str:
        """生成事件上下文（使用AI，基于历史事件推演，避免重复，支持场景切换）"""
        # 构建历史事件摘要
        history_summary = ""
        if previous_events:
            history_summary = "\n".join([f"- {event[:200]}" for event in previous_events[:5]])  # 增加历史事件数量
        else:
            history_summary = "这是第一个中间事件。"
        
        # 获取场景描述
        scene_info = SCENES.get(current_scene, {})
        scene_name = scene_info.get('name', current_scene)
        scene_desc = scene_info.get('description', f'在{scene_name}的场景中')
        
        # 构建已发生的事件摘要（避免重复）
        previous_summary = ""
        if self.previous_event_contexts:
            previous_summary = "\n已发生的事件摘要（不要重复）：\n" + "\n".join([f"- {ctx[:100]}" for ctx in self.previous_event_contexts[-5:]])
        
        # 获取场景信息
        scene_name = SCENES.get(current_scene, {}).get('name', current_scene)
        
        # 使用AI生成事件上下文
        prompt = f"""你是一个剧情游戏的事件上下文生成器。请根据以下信息生成一个事件描述（30-50字）：

【历史事件】（必须参考，确保连续性）：
{history_summary}
{previous_summary}

【当前场景】：
{scene_name}（{current_scene}）
场景描述：{scene_desc}

事件序号：第{event_number}个中间事件

要求：
1. 【连续性】基于历史事件合理推演新的事件，必须与历史事件有连续性，不能突兀
2. 【不重复】不要重复之前已经发生过的场景和事件，要推进剧情发展，创造新的情节
3. 【场景切换】可以自然地切换场景（如从学校到咖啡厅、从教室到操场、从图书馆到书店等），但要符合逻辑，有合理的过渡
4. 【具体情境】描述一个具体的事件情境（如：在咖啡厅偶遇、在操场上一起跑步、在图书馆一起学习、在书店选书等）
5. 【剧情推进】事件要有新的进展，推进剧情发展，不能原地踏步
6. 【场景描述】明确描述当前场景，让玩家知道在哪里
7. 只描述事件情境，不要包含对话
8. 【避免重复】检查历史事件和已发生事件，确保新事件与之前的事件不重复，有新的内容

事件描述："""
        
        try:
            from game.ai_generator import AIGenerator
            ai_gen = AIGenerator()
            if ai_gen.enabled:
                from dashscope import Generation
                response = Generation.call(
                    model='qwen-turbo',
                    prompt=prompt,
                    max_tokens=150,
                    temperature=0.9
                )
                
                if response.status_code == 200:
                    context = response.output.text.strip()
                    # 清理可能的引号
                    context = context.strip('"').strip("'").strip()
                    return context
        except Exception as e:
            print(f"[警告] AI生成事件上下文失败: {e}")
        
        # 回退到规则生成
        return f"在{scene_name}，剧情继续发展..."
    
    def get_ending_event(self, character_id: int) -> Dict:
        """获取结尾事件（根据状态值判定）"""
        states = self.db_manager.get_character_states(character_id)
        attributes = self.db_manager.get_character_attributes(character_id)
        
        # 根据状态值判定结局类型
        favorability = states.favorability if states else 0.0
        trust = states.trust if states else 0.0
        hostility = states.hostility if states else 0.0
        
        # 判定结局
        if favorability > 70 and trust > 60 and hostility < 20:
            ending_type = "happy_ending"
            event_context = "经过一系列事件，你们的关系变得更加亲密，这是一个美好的结局。"
        elif favorability < 30 or hostility > 50:
            ending_type = "bad_ending"
            event_context = "关系走向了不好的方向，你们之间的距离越来越远。"
        elif trust > 50 and favorability > 40:
            ending_type = "neutral_ending"
            event_context = "你们的关系保持在一个稳定的状态，未来还有无限可能。"
        else:
            ending_type = "open_ending"
            event_context = "故事还在继续，结局尚未确定..."
        
        event = self.event_generator.generate_event(
            character_id=character_id,
            event_id=f"ending_{ending_type}",
            event_context=event_context
        )
        
        event['title'] = "结局"
        event['ending_type'] = ending_type
        event['event_context'] = event_context
        self.current_event = event
        self.dialogue_history = []  # 重置对话历史
        
        return event
    
    def record_character_dialogue(self, dialogue: str):
        """记录角色对话到对话历史"""
        if dialogue:
            self.dialogue_history.append({
                'type': 'character',
                'content': dialogue
            })
    
    def process_player_choice(self, character_id: int, choice: Dict):
        """处理玩家选择，更新状态值并记录对话历史"""
        # 记录玩家选择到对话历史
        if choice.get('text'):
            self.dialogue_history.append({
                'type': 'player',
                'content': choice['text']
            })
        
        # 更新状态值
        if choice['type'] != 'neutral' and choice.get('state_changes'):
            self.db_manager.update_character_states(
                character_id=character_id,
                state_changes=choice['state_changes']
            )
    
    def get_next_dialogue_round(self, character_id: int) -> Dict:
        """获取下一轮对话（角色对话 + 玩家选项）"""
        if not self.current_event:
            raise ValueError("当前没有活动的事件")
        
        # 计算当前对话轮次（每轮包含角色对话+玩家选择）
        dialogue_round = (len(self.dialogue_history) // 2) + 1
        
        # 从向量数据库检索最近的对话内容（用于推演）
        recent_dialogues = self.event_generator.vector_db.search_recent_dialogues(
            character_id=character_id,
            event_id=self.current_event['event_id'],
            n_results=5
        )
        
        # 提取之前的对话内容（用于连贯性）
        previous_dialogues = []
        for item in self.dialogue_history:
            if item['type'] == 'character':
                previous_dialogues.append(f"角色: {item['content']}")
            elif item['type'] == 'player':
                previous_dialogues.append(f"玩家: {item['content']}")
        
        # 如果向量数据库中有最近的对话，也加入上下文
        if recent_dialogues.get('documents') and len(recent_dialogues['documents']) > 0:
            # 将向量数据库中的对话内容也加入上下文
            vector_dialogues = recent_dialogues['documents'][:3]  # 只取最近3条
            previous_dialogues.extend([f"[历史] {d[:100]}" for d in vector_dialogues])
        
        # 生成对话轮次
        dialogue_data = self.event_generator.generate_dialogue_round(
            character_id=character_id,
            story_background=self.current_event['story_background'],
            dialogue_round=dialogue_round,
            previous_dialogues=previous_dialogues
        )
        
        return dialogue_data
    
    def should_continue_dialogue(self) -> bool:
        """判断是否应该继续对话（至少4轮）"""
        # 如果对话轮次少于最少轮数，继续对话
        if len(self.dialogue_history) < self.min_dialogue_rounds:
            return True
        
        # 可以添加其他条件，比如根据状态值判断是否自然结束对话
        # 目前至少4轮后可以结束
        return False
    
    def save_dialogue_round_to_vector_db(self, character_id: int, dialogue_round: int):
        """将当前轮次的对话保存到向量数据库"""
        if not self.current_event:
            return
        
        # 获取本轮对话内容
        character_dialogue = None
        player_choice = None
        
        # 从对话历史中提取本轮对话（最后两条应该是角色对话和玩家选择）
        if len(self.dialogue_history) >= 2:
            # 检查最后两条
            last_two = self.dialogue_history[-2:]
            for item in last_two:
                if item['type'] == 'character' and not character_dialogue:
                    character_dialogue = item['content']
                elif item['type'] == 'player' and not player_choice:
                    player_choice = item['content']
        
        # 如果找到了对话内容，保存到向量数据库
        if character_dialogue and player_choice:
            self.event_generator.vector_db.add_dialogue_round(
                character_id=character_id,
                event_id=self.current_event['event_id'],
                story_background=self.current_event['story_background'],
                dialogue_round=dialogue_round,
                character_dialogue=character_dialogue,
                player_choice=player_choice,
                metadata={
                    'event_context': self.current_event.get('event_context', ''),
                    'title': self.current_event.get('title', ''),
                    'scene': self.current_event.get('scene', '')
                }
            )
    
    def save_event_to_vector_db(self, character_id: int):
        """将当前事件的所有对话保存到向量数据库（保留用于完整事件保存）"""
        if not self.current_event:
            return
        
        # 组合所有对话内容（包含角色对话和玩家选择）
        all_dialogues = []
        for item in self.dialogue_history:
            if item['type'] == 'character':
                all_dialogues.append(f"角色: {item['content']}")
            elif item['type'] == 'player':
                all_dialogues.append(f"玩家: {item['content']}")
        
        dialogue_text = "\n".join(all_dialogues) if all_dialogues else "无对话"
        
        # 保存到向量数据库（包含故事背景和完整对话）
        self.event_generator.vector_db.add_event(
            character_id=character_id,
            event_id=self.current_event['event_id'],
            story_text=self.current_event['story_background'],
            dialogue_text=dialogue_text,
            metadata={
                'event_context': self.current_event.get('event_context', ''),
                'dialogue_rounds': len([d for d in self.dialogue_history if d['type'] == 'player']),
                'title': self.current_event.get('title', ''),
                'type': 'complete_event'  # 标记为完整事件
            }
        )
    
    def get_next_event(self, character_id: int, scene_id: str = 'school') -> Dict:
        """获取下一个事件"""
        if self.current_event_count == 0:
            # 开头事件
            return self.get_opening_event(character_id, scene_id)
        elif self.current_event_count <= config.GAME_CONFIG['max_events']:
            # 中间事件（从1开始计数，因为开头事件是第0个）
            return self.get_middle_event(character_id, self.current_event_count)
        else:
            # 结尾事件
            return self.get_ending_event(character_id)
    
    def get_current_scene(self) -> str:
        """获取当前场景"""
        return self.current_scene
    
    def is_game_finished(self) -> bool:
        """判断游戏是否结束"""
        # 当完成中间事件后，下一次获取事件时就是结尾
        return self.current_event_count > config.GAME_CONFIG['max_events']

