"""API数据模型（Pydantic Schemas）"""
from typing import Optional, Dict, Any, List, TypeVar, Generic
from pydantic import BaseModel, Field


# ========== 泛型响应包装 ==========

T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """通用API响应包装 {code, message, data}"""
    code: int = Field(default=200, description="状态码，200表示成功")
    message: str = Field(default="ok", description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")


class ErrorResponse(BaseModel):
    """统一错误响应"""
    code: int = Field(..., description="错误码（4xx/5xx）")
    message: str = Field(..., description="错误消息")
    data: None = Field(default=None, description="错误时为null")


# ========== 请求模型 ==========

class CreateCharacterRequest(BaseModel):
    """创建角色请求"""
    name: str = Field(..., description="角色名称")
    appearance: Dict[str, Any] = Field(..., description="外观设定")
    personality: Dict[str, Any] = Field(..., description="性格设定")
    background: Dict[str, Any] = Field(..., description="背景设定")
    gender: Optional[str] = Field(None, description="性别（可选）")
    age: Optional[int] = Field(None, description="年龄（可选）")
    identity: Optional[str] = Field(None, description="身份（可选）")
    initial_scene: Optional[str] = Field(None, description="初始场景（可选）")
    initial_scene_prompt: Optional[str] = Field(None, description="初始场景提示（可选）")
    user_id: Optional[str] = Field(None, description="玩家ID（可选，用于图片文件命名）")
    image_type: Optional[str] = Field('portrait', description="图片类型（portrait=立绘, avatar=头像, scene=场景图，默认：portrait）")


class GameInitRequest(BaseModel):
    """初始化游戏请求"""
    user_id: Optional[str] = Field(None, description="用户ID（可选，不提供则自动生成）")
    game_mode: str = Field(..., description="游戏模式：'solo' | 'story'")
    character_id: Optional[str] = Field(None, description="角色ID（可选）")


class GameInputRequest(BaseModel):
    """处理玩家输入请求"""
    thread_id: str = Field(..., description="线程ID")
    user_input: str = Field(..., description="玩家输入内容")
    user_id: Optional[str] = Field(None, description="用户ID（可选）")
    character_id: Optional[str] = Field(None, description="角色ID（可选，用于会话恢复）")


class TriggerEndingRequest(BaseModel):
    """触发结局请求"""
    thread_id: str = Field(..., description="线程ID")


class InitializeStoryRequest(BaseModel):
    """初始化故事请求"""
    thread_id: str = Field(..., description="线程ID")
    character_id: str = Field(..., description="角色ID")
    scene_id: Optional[str] = Field('school', description="初遇大场景ID（可选，默认：school）")
    opening_event_id: Optional[str] = Field(None, description="初遇事件ID（可选，如果不提供则随机选择）")
    character_image_url: Optional[str] = Field(None, description="用户选择的角色图片URL（可选，如果不提供则使用最新图片）")


class RemoveBackgroundRequest(BaseModel):
    """去除背景请求"""
    image_url: Optional[str] = Field(None, description="图片URL（可选，如果不提供则使用角色最新图片）")
    image_urls: Optional[List[str]] = Field(None, description="所有图片URL列表（用于删除未选中的图片）")
    selected_index: Optional[int] = Field(None, description="选中的图片索引（0, 1, 2）")


# ========== 响应数据模型（data 字段内的类型） ==========

class CharacterData(BaseModel):
    """角色信息数据"""
    character_id: str
    name: str
    appearance: Dict[str, Any]
    personality: Dict[str, Any]
    background: Dict[str, Any]
    gender: Optional[str] = None
    age: Optional[int] = None
    identity: Optional[str] = None
    initial_scene: Optional[str] = None
    image_urls: Optional[List[str]] = Field(None, description="角色图片URL列表")


class GameInitData(BaseModel):
    """初始化游戏数据"""
    thread_id: str
    user_id: str
    game_mode: str


class GameInputData(BaseModel):
    """玩家输入响应数据"""
    character_dialogue: Optional[str] = None
    player_options: Optional[List[Dict[str, Any]]] = None
    story_background: Optional[str] = None
    event_title: Optional[str] = None
    scene: Optional[str] = None
    is_event_finished: bool = False
    is_game_finished: bool = False
    # 会话恢复时的额外字段
    thread_id: Optional[str] = None
    session_restored: Optional[bool] = None
    need_reselect_option: Optional[bool] = None
    restored_from_thread_id: Optional[str] = None


class CheckEndingData(BaseModel):
    """结局检查数据"""
    has_ending: bool = Field(..., description="是否满足结局条件")
    ending: Optional[Dict[str, Any]] = Field(None, description="结局信息")


class TriggerEndingData(BaseModel):
    """触发结局数据"""
    thread_id: Optional[str] = None
    ending: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class SceneItem(BaseModel):
    """大场景条目"""
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    imageUrl: Optional[str] = None
    openingEventsCount: Optional[int] = None


class SceneListData(BaseModel):
    """场景列表数据"""
    scenes: List[SceneItem] = Field(default_factory=list)


class OpeningEventItem(BaseModel):
    """初遇事件条目"""
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    sub_scene: Optional[str] = None


class OpeningEventsData(BaseModel):
    """初遇事件列表数据"""
    major_scene_id: str
    major_scene_name: Optional[str] = None
    events: List[OpeningEventItem] = Field(default_factory=list)


class CharacterImagesData(BaseModel):
    """角色图片数据"""
    images: List[str] = Field(default_factory=list)


class RemoveBackgroundData(BaseModel):
    """去除背景数据"""
    selected_image_url: Optional[str] = None
    transparent_url: Optional[str] = None
    local_path: Optional[str] = None
    deleted_count: Optional[int] = 0


class InitializeStoryData(BaseModel):
    """初始化故事数据"""
    thread_id: Optional[str] = None
    scene: Optional[str] = None
    scene_image_url: Optional[str] = None
    composite_image_url: Optional[str] = None
    story_background: Optional[str] = None
    character_dialogue: Optional[str] = None
    player_options: Optional[List[Dict[str, Any]]] = None
    is_game_finished: Optional[bool] = False


# ========== 完整 API 响应模型（含包装） ==========

# --- Game Routes ---
GameInitApiResponse = ApiResponse[GameInitData]
GameInputApiResponse = ApiResponse[GameInputData]
CheckEndingApiResponse = ApiResponse[CheckEndingData]
TriggerEndingApiResponse = ApiResponse[TriggerEndingData]

# --- Character Routes ---
CreateCharacterApiResponse = ApiResponse[CharacterData]
SceneListApiResponse = ApiResponse[SceneListData]
OpeningEventsApiResponse = ApiResponse[OpeningEventsData]
CharacterApiResponse = ApiResponse[CharacterData]
CharacterImagesApiResponse = ApiResponse[CharacterImagesData]
RemoveBackgroundApiResponse = ApiResponse[RemoveBackgroundData]
InitializeStoryApiResponse = ApiResponse[InitializeStoryData]


# ========== 向后兼容别名（保留旧名称） ==========
CharacterResponse = CharacterData
GameInitResponse = GameInitData
GameInputResponse = GameInputData
CheckEndingResponse = CheckEndingData
CharacterImagesResponse = CharacterImagesData
