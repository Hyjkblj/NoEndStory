"""PostgreSQL数据库管理"""
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from models.character import Base, Character, CharacterAttribute, CharacterState
import config


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        # 使用 SQLAlchemy URL 构建器，自动处理密码中的特殊字符（P0-6）
        url = URL.create(
            drivername="postgresql",
            username=config.DB_CONFIG['user'],
            password=config.DB_CONFIG['password'],
            host=config.DB_CONFIG['host'],
            port=config.DB_CONFIG['port'],
            database=config.DB_CONFIG['database'],
        )
        self.engine = create_engine(
            url,
            pool_pre_ping=True,  # 自动重连
            pool_size=20,        # 常驻连接数（P1 优化）
            max_overflow=40,     # 溢出连接数
            pool_recycle=3600,   # 1小时回收连接
            connect_args={
                "connect_timeout": 10,
                "application_name": "noendstory",
            }
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
                        personality: str, attributes: dict, scene_id: str = 'school',
                        character_data: dict = None) -> int:
        """创建角色
        
        Args:
            name: 角色名称
            gender: 性别
            appearance: 外观描述（文本，用于兼容）
            personality: 性格描述（文本，用于兼容）
            attributes: 角色属性字典（用于兼容旧系统）
            scene_id: 场景ID
            character_data: 完整的角色数据字典（新系统，包含所有前端数据）
        
        Returns:
            角色ID（用于与ChromaDB关联）
        """
        with self.get_session() as session:
            # 创建角色
            character = Character(
                name=name,
                gender=gender,
                appearance=appearance,
                personality=personality,
                scene_id=scene_id,
                character_data=character_data  # 存储完整的角色数据字典
            )
            session.add(character)
            session.flush()
            
            # 添加决定因素（保留用于兼容）
            if attributes:
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
            return character.id  # 返回角色ID，作为与ChromaDB关联的key
    
    def get_character(self, character_id: int) -> Character:
        """获取角色信息
        
        Returns:
            Character对象，包含character_data字段（完整的角色数据字典）
        """
        with self.get_session() as session:
            character = session.query(Character).filter(Character.id == character_id).first()
            return character
    
    def get_character_data(self, character_id: int) -> dict:
        """获取角色的完整数据字典
        
        Args:
            character_id: 角色ID（与ChromaDB关联的key）
        
        Returns:
            完整的角色数据字典，如果不存在则返回None
        """
        with self.get_session() as session:
            character = session.query(Character).filter(Character.id == character_id).first()
            if character and character.character_data:
                return character.character_data
            return None
    
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

