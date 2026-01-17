"""角色管理API路由"""
from fastapi import APIRouter, HTTPException
from typing import List
from api.schemas import (
    CreateCharacterRequest,
    CharacterResponse,
    CharacterImagesResponse,
    InitializeStoryRequest
)
from api.response import success_response, error_response, not_found_response
from api.services.character_service import CharacterService
from api.services.game_service import GameService

router = APIRouter(prefix="/v1/characters", tags=["角色管理"])

character_service = CharacterService()
game_service = GameService()


@router.post("/create", response_model=dict)
async def create_character(request: CreateCharacterRequest):
    """创建新角色"""
    try:
        # 转换请求数据
        request_data = request.dict()
        
        # 创建角色
        character_id = character_service.create_character(request_data)
        
        # 获取角色信息
        character_info = character_service.get_character(character_id)
        
        return success_response(data=character_info)
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"创建角色错误详情:\n{error_detail}")  # 输出到控制台
        return error_response(
            code=500,
            message=f"创建角色失败: {str(e)}",
            error={
                "type": type(e).__name__,
                "details": {
                    "message": str(e)
                }
            }
        )


@router.get("/{character_id}", response_model=dict)
async def get_character(character_id: str):
    """获取角色信息"""
    try:
        character_id_int = int(character_id)
        character_info = character_service.get_character(character_id_int)
        return success_response(data=character_info)
    except ValueError:
        return error_response(code=400, message="无效的角色ID")
    except Exception as e:
        if "不存在" in str(e):
            return not_found_response(message="角色不存在")
        return error_response(code=500, message=f"获取角色失败: {str(e)}")


@router.get("/{character_id}/images", response_model=dict)
async def get_character_images(character_id: str):
    """获取角色图片列表"""
    try:
        character_id_int = int(character_id)
        images = character_service.get_character_images(character_id_int)
        return success_response(data={"images": images})
    except ValueError:
        return error_response(code=400, message="无效的角色ID")
    except Exception as e:
        return error_response(code=500, message=f"获取角色图片失败: {str(e)}")


@router.post("/initialize-story", response_model=dict)
async def initialize_story(request: InitializeStoryRequest):
    """初始化故事（触发初遇场景）"""
    try:
        character_id = int(request.character_id)
        result = game_service.initialize_story(request.thread_id, character_id)
        return success_response(data=result)
    except ValueError as e:
        return error_response(code=400, message=f"参数错误: {str(e)}")
    except Exception as e:
        return error_response(code=500, message=f"初始化故事失败: {str(e)}")

