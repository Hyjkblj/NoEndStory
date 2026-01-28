"""API数据模型（Pydantic Schemas）"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    """通用API响应格式"""
    code: int = Field(default=200, description="状态码，200表示成功")
    message: str = Field(default="success", description="响应消息")
    data: Any = Field(default=None, description="响应数据")


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


class CharacterResponse(BaseModel):
    """角色信息响应"""
    character_id: str
    name: str
    appearance: Dict[str, Any]
    personality: Dict[str, Any]
    background: Dict[str, Any]
    gender: Optional[str] = None
    age: Optional[int] = None
    identity: Optional[str] = None
    initial_scene: Optional[str] = None
    image_urls: Optional[List[str]] = Field(None, description="角色图片URL列表（组图，供前端三选一）")


class GameInitRequest(BaseModel):
    """初始化游戏请求"""
    user_id: Optional[str] = Field(None, description="用户ID（可选，不提供则自动生成）")
    game_mode: str = Field(..., description="游戏模式：'solo' | 'story'")
    character_id: Optional[str] = Field(None, description="角色ID（可选）")


class GameInitResponse(BaseModel):
    """初始化游戏响应"""
    thread_id: str
    user_id: str
    game_mode: str


class GameInputRequest(BaseModel):
    """处理玩家输入请求"""
    thread_id: str = Field(..., description="线程ID")
    user_input: str = Field(..., description="玩家输入内容")
    user_id: Optional[str] = Field(None, description="用户ID（可选）")
    character_id: Optional[str] = Field(None, description="角色ID（可选，用于会话恢复）")


class GameInputResponse(BaseModel):
    """处理玩家输入响应"""
    character_dialogue: Optional[str] = None
    player_options: Optional[List[Dict[str, Any]]] = None
    story_background: Optional[str] = None
    event_title: Optional[str] = None
    scene: Optional[str] = None
    is_event_finished: bool = False
    is_game_finished: bool = False


class CheckEndingResponse(BaseModel):
    """检查结局响应"""
    has_ending: bool = Field(..., description="是否满足结局条件")
    ending: Optional[Dict[str, Any]] = Field(None, description="结局信息（如果满足条件）")


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


class CharacterImagesResponse(BaseModel):
    """角色图片响应"""
    images: List[str] = Field(default_factory=list, description="图片URL数组")


class RemoveBackgroundRequest(BaseModel):
    """去除背景请求"""
    image_url: Optional[str] = Field(None, description="图片URL（可选，如果不提供则使用角色最新图片）")
    image_urls: Optional[List[str]] = Field(None, description="所有图片URL列表（用于删除未选中的图片）")
    selected_index: Optional[int] = Field(None, description="选中的图片索引（0, 1, 2）")
