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
        
        # 输出前端接收的人物设定数据到控制台
        import json
        print("\n" + "="*80)
        print("【前端接收的人物设定数据】")
        print("="*80)
        print(f"角色名称: {request_data.get('name', '未命名')}")
        print(f"性别: {request_data.get('gender', '未指定')}")
        print(f"年龄: {request_data.get('age', '未指定')}")
       
        
        # 外观设定
        appearance = request_data.get('appearance', {})
        print(f"\n外观设定:")
        if isinstance(appearance, dict):
            for key, value in appearance.items():
                if isinstance(value, (list, dict)):
                    print(f"  - {key}: {json.dumps(value, ensure_ascii=False, indent=4)}")
                else:
                    print(f"  - {key}: {value}")
        else:
            print(f"  {appearance}")
        
        # 性格设定
        personality = request_data.get('personality', {})
        print(f"\n性格设定:")
        if isinstance(personality, dict):
            for key, value in personality.items():
                if isinstance(value, (list, dict)):
                    print(f"  - {key}: {json.dumps(value, ensure_ascii=False, indent=4)}")
                else:
                    print(f"  - {key}: {value}")
        else:
            print(f"  {personality}")
        
        # 生成角色图片的prompt（包含组图指令）
        image_prompt = character_service.generate_character_image_prompt(
            request_data, 
            generate_group=True,  # 启用组图
            group_count=3  # 生成3张图片
        )
        print(f"\n【角色图片生成Prompt】")
        print("="*80)
        print(image_prompt)
        print("="*80 + "\n")
        
        # 创建角色
        character_id = character_service.create_character(request_data)
        
        # 生成角色组图（如果服务已启用）
        # 获取user_id和image_type（用于文件命名）
        user_id = request_data.get('user_id')
        image_type = request_data.get('image_type', 'portrait')
        image_urls = None
        try:
            image_urls = character_service.generate_character_image(
                request_data, character_id, user_id, image_type,
                generate_group=True, group_count=3  # 生成3张图片供前端三选一
            )
            if image_urls:
                print(f"[信息] 角色组图生成成功: 共 {len(image_urls)} 张图片")
                for i, url in enumerate(image_urls, 1):
                    print(f"[信息] 图片 {i}: {url}")
        except Exception as e:
            print(f"[警告] 角色图片生成失败: {e}")
            import traceback
            print(traceback.format_exc())
        
        # 获取角色信息
        character_info = character_service.get_character(character_id)
        
        # 添加图片URL列表到响应
        if image_urls:
            character_info['image_urls'] = image_urls
        
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

