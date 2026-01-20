"""PostgreSQL数据库管理"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from models.character import Base, Character, CharacterAttribute, CharacterState
import config


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.engine = create_engine(
            f"postgresql://{config.DB_CONFIG['user']}:{config.DB_CONFIG['password']}"
            f"@{config.DB_CONFIG['host']}:{config.DB_CONFIG['port']}/{config.DB_CONFIG['database']}",
            pool_pre_ping=True  # 自动重连
        )
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
    
    def init_db(self):
        """初始化数据库表"""
        Base.metadata.create_all(self.engine)
    
    @contextmanager
    def get_session(self):
        """获取数据库会话"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_character(self, name: str, gender: str, appearance: str, 
                        personality: str, attributes: dict, scene_id: str = 'school') -> int:
        """创建角色"""
        with self.get_session() as session:
            # 创建角色
            character = Character(
                name=name,
                gender=gender,
                appearance=appearance,
                personality=personality,
                scene_id=scene_id
            )
            session.add(character)
            session.flush()
            
            # 添加决定因素
            for attr_type, attr_value in attributes.items():
                attr = CharacterAttribute(
                    character_id=character.id,
                    attribute_type=attr_type,
                    attribute_value=attr_value
                )
                session.add(attr)
            
            # 初始化状态值
            state = CharacterState(character_id=character.id)
            session.add(state)
            
            session.commit()
            return character.id
    
    def get_character(self, character_id: int) -> Character:
        """获取角色信息"""
        with self.get_session() as session:
            character = session.query(Character).filter(Character.id == character_id).first()
            return character
    
    def get_character_states(self, character_id: int) -> CharacterState:
        """获取角色状态值"""
        with self.get_session() as session:
            state = session.query(CharacterState).filter(
                CharacterState.character_id == character_id
            ).first()
            if state:
                # 在会话关闭前访问所有属性，确保数据已加载
                _ = state.favorability, state.trust, state.hostility, state.dependence, \
                    state.emotion, state.stress, state.anxiety, state.happiness, \
                    state.sadness, state.confidence, state.initiative, state.caution
            return state
    
    def update_character_states(self, character_id: int, state_changes: dict):
        """更新角色状态值"""
        with self.get_session() as session:
            state = session.query(CharacterState).filter(
                CharacterState.character_id == character_id
            ).first()
            
            if state:
                for key, value in state_changes.items():
                    if hasattr(state, key):
                        current_value = getattr(state, key)
                        new_value = max(0, min(100, current_value + value))  # 限制在0-100范围
                        setattr(state, key, new_value)
            
            session.commit()
    
    def get_character_attributes(self, character_id: int) -> dict:
        """获取角色所有决定因素"""
        with self.get_session() as session:
            attributes = session.query(CharacterAttribute).filter(
                CharacterAttribute.character_id == character_id
            ).all()
            
            return {attr.attribute_type: attr.attribute_value for attr in attributes}

