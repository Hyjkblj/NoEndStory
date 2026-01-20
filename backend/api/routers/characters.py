"""角色管理API路由"""
from fastapi import APIRouter, HTTPException
from typing import List
from api.schemas import (
    CreateCharacterRequest,
    CharacterResponse,
    CharacterImagesResponse,
    InitializeStoryRequest,
    RemoveBackgroundRequest
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


@router.get("/scenes", response_model=dict)
async def get_scenes():
    """获取可用场景列表（用于初遇场景选择）
    
    场景名称由图片文件名决定，支持多种命名格式：
    1. {scene_id}_{场景名称}.{ext} - 格式：school_学校.jpg
    2. {scene_id}.{ext} - 格式：school.jpg（使用scenes.py中的名称）
    3. {场景名称}.{ext} - 格式：餐厅.jpeg（纯中文，通过名称匹配scenes.py中的场景）
    """
    try:
        from data.scenes import SCENES
        import os
        import config
        
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if os.path.isabs(config.SCENE_IMAGE_SAVE_DIR):
            scene_images_dir = config.SCENE_IMAGE_SAVE_DIR
        else:
            scene_images_dir = os.path.join(backend_dir, config.SCENE_IMAGE_SAVE_DIR)
        
        # 获取所有场景图片文件
        # 格式1: {scene_id}_{场景名称}.{ext} -> {'scene_id': {'url': ..., 'name': '场景名称'}}
        # 格式2: {scene_id}.{ext} -> {'scene_id': {'url': ..., 'name': None}}
        # 格式3: {场景名称}.{ext} -> {'场景名称': {'url': ..., 'name': '场景名称', 'scene_id': None}}
        scene_images_by_id = {}  # 按scene_id索引
        scene_images_by_name = {}  # 按场景名称索引（用于纯中文文件名）
        
        if os.path.exists(scene_images_dir):
            image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            for filename in os.listdir(scene_images_dir):
                # 检查是否是图片文件
                if any(filename.lower().endswith(ext) for ext in image_extensions):
                    name_without_ext = os.path.splitext(filename)[0]
                    
                    # 尝试匹配格式：scene_id_场景名称
                    parts = name_without_ext.split('_', 1)
                    if len(parts) == 2:
                        # 格式1: {scene_id}_{场景名称}.{ext}
                        scene_id_from_file = parts[0]
                        scene_name_from_file = parts[1]
                        scene_images_by_id[scene_id_from_file] = {
                            'filename': filename,
                            'url': f"/static/images/scenes/{filename}",
                            'name': scene_name_from_file
                        }
                    else:
                        # 可能是格式2或格式3
                        # 先检查是否是已知的scene_id
                        if name_without_ext in SCENES:
                            # 格式2: {scene_id}.{ext}
                            scene_images_by_id[name_without_ext] = {
                                'filename': filename,
                                'url': f"/static/images/scenes/{filename}",
                                'name': None  # 使用scenes.py中的名称
                            }
                        else:
                            # 格式3: {场景名称}.{ext}（纯中文文件名）
                            scene_images_by_name[name_without_ext] = {
                                'filename': filename,
                                'url': f"/static/images/scenes/{filename}",
                                'name': name_without_ext
                            }
        
        scenes_list = []
        processed_scene_ids = set()  # 记录已处理的场景ID
        
        # 首先处理所有有图片的场景（优先使用图片文件名中的场景名称）
        # 1. 处理 scene_images_by_id 中的所有场景（格式：{scene_id}_{场景名称}.{ext}）
        for scene_id_from_file, image_info in scene_images_by_id.items():
            processed_scene_ids.add(scene_id_from_file)
            
            # 检查场景是否在 SCENES 中有定义
            if scene_id_from_file in SCENES:
                scene_info = SCENES[scene_id_from_file]
                # 使用图片文件名中的场景名称（如果存在）
                scene_name = image_info['name'] if image_info['name'] else scene_info.get('name', scene_id_from_file)
                scene_description = scene_info.get('description', f'在{scene_name}中初次相遇')
                opening_events = scene_info.get('opening_events', [{
                    'id': f'{scene_id_from_file}_meet',
                    'title': f'在{scene_name}初遇',
                    'description': f'在{scene_name}中，你们第一次相遇'
                }])
            else:
                # 场景不在 SCENES 中，使用图片文件名中的信息
                scene_name = image_info['name'] if image_info['name'] else scene_id_from_file
                scene_description = f'在{scene_name}中初次相遇'
                opening_events = [{
                    'id': f'{scene_id_from_file}_meet',
                    'title': f'在{scene_name}初遇',
                    'description': f'在{scene_name}中，你们第一次相遇'
                }]
            
            scenes_list.append({
                'id': scene_id_from_file,
                'name': scene_name,  # 由图片文件名决定
                'description': scene_description,
                'imageUrl': image_info['url'],
                'openingEvents': opening_events
            })
            print(f"[信息] 添加场景: {scene_id_from_file} ({scene_name})")
        
        # 2. 处理 scene_images_by_name 中未匹配的场景（格式：{场景名称}.{ext}）
        for scene_name_from_file, image_info in scene_images_by_name.items():
            # 检查是否已经匹配到已知场景（通过场景名称）
            matched_scene_id = None
            for scene_id, scene_info in SCENES.items():
                if scene_info.get('name') == scene_name_from_file:
                    matched_scene_id = scene_id
                    break
            
            if matched_scene_id:
                # 如果匹配到已知场景，且该场景还没有被处理，则添加
                if matched_scene_id not in processed_scene_ids:
                    processed_scene_ids.add(matched_scene_id)
                    scene_info = SCENES[matched_scene_id]
                    scenes_list.append({
                        'id': matched_scene_id,
                        'name': image_info['name'],  # 使用文件名中的名称
                        'description': scene_info.get('description', f'在{image_info["name"]}中初次相遇'),
                        'imageUrl': image_info['url'],
                        'openingEvents': scene_info.get('opening_events', [{
                            'id': f'{matched_scene_id}_meet',
                            'title': f'在{image_info["name"]}初遇',
                            'description': f'在{image_info["name"]}中，你们第一次相遇'
                        }])
                    })
                    print(f"[信息] 通过名称匹配添加场景: {matched_scene_id} ({image_info['name']})")
            else:
                # 未匹配到已知场景，创建新场景（使用文件名作为场景ID）
                scene_id_from_name = scene_name_from_file
                scenes_list.append({
                    'id': scene_id_from_name,
                    'name': image_info['name'],  # 使用文件名作为场景名称
                    'description': f'在{image_info["name"]}中初次相遇',
                    'imageUrl': image_info['url'],
                    'openingEvents': [{
                        'id': f'{scene_id_from_name}_meet',
                        'title': f'在{image_info["name"]}初遇',
                        'description': f'在{image_info["name"]}中，你们第一次相遇'
                    }]
                })
                print(f"[信息] 为图片文件创建新场景: {scene_id_from_name} ({image_info['name']})")
        
        # 3. 处理 SCENES 中有 opening_events 但没有图片的场景（确保这些场景也能显示）
        for scene_id, scene_info in SCENES.items():
            if scene_id not in processed_scene_ids and 'opening_events' in scene_info:
                scenes_list.append({
                    'id': scene_id,
                    'name': scene_info.get('name', scene_id),
                    'description': scene_info.get('description', ''),
                    'imageUrl': None,  # 没有图片
                    'openingEvents': scene_info.get('opening_events', [])
                })
                print(f"[信息] 添加无图片的场景: {scene_id}")
        
        print(f"[信息] 总共返回 {len(scenes_list)} 个场景")
        return success_response(data={'scenes': scenes_list})
    except Exception as e:
        import traceback
        print(f"[错误] 获取场景列表失败: {e}")
        print(traceback.format_exc())
        return error_response(code=500, message=f"获取场景列表失败: {str(e)}")


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


@router.post("/{character_id}/remove-background", response_model=dict)
async def remove_character_background(character_id: str, request: RemoveBackgroundRequest = RemoveBackgroundRequest()):
    """去除角色图片背景（使用rembg的isnet-general-use模型）
    
    Args:
        character_id: 角色ID
        request: 请求体，包含image_url（可选）、image_urls（所有图片URL列表）、selected_index（选中的索引）
    """
    try:
        # 解析请求体
        image_url = request.image_url if request else None
        image_urls = request.image_urls if request else None
        selected_index = request.selected_index if request else None
        
        character_id_int = int(character_id)
        
        # 获取图片服务
        from api.services.image_service import ImageService
        image_service = ImageService()
        
        # 如果没有提供image_url，获取角色最新图片
        if not image_url:
            images = character_service.get_character_images(character_id_int)
            if not images or len(images) == 0:
                return error_response(code=404, message="角色没有图片")
            # 使用最新图片（第一张）
            image_url = images[0]
        
        print(f"[API] 开始去除角色 {character_id_int} 的图片背景: {image_url}")
        
        # 使用rembg去除背景，并重命名为标准格式
        output_path = image_service.remove_background_with_rembg(
            image_path=image_url,
            character_id=character_id_int,
            rename_to_standard=True  # 重命名为标准格式
        )
        
        if not output_path:
            return error_response(code=500, message="背景去除失败")
        
        # 删除未选中的图片（如果有提供image_urls和selected_index）
        deleted_count = 0
        if image_urls and selected_index is not None and len(image_urls) > 1:
            deleted_count = image_service.delete_unselected_character_images(
                character_id=character_id_int,
                image_urls=image_urls,
                selected_index=selected_index
            )
            print(f"[API] 已删除 {deleted_count} 张未选中的图片")
        
        # 构建返回的URL（静态文件路径）
        import os
        filename = os.path.basename(output_path)
        result_url = f"/static/images/characters/{filename}"
        
        print(f"[API] 背景去除成功: {result_url}")
        return success_response(data={
            "original_url": image_url,
            "transparent_url": result_url,
            "local_path": output_path,
            "deleted_count": deleted_count
        })
        
    except ValueError:
        return error_response(code=400, message="无效的角色ID")
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[API错误] 去除背景失败: {str(e)}")
        print(error_trace)
        return error_response(code=500, message=f"去除背景失败: {str(e)}", error={"traceback": error_trace})


@router.post("/initialize-story", response_model=dict)
async def initialize_story(request: InitializeStoryRequest):
    """初始化故事（触发初遇场景）"""
    try:
        character_id = int(request.character_id)
        scene_id = request.scene_id or 'school'  # 默认使用school场景
        character_image_url = request.character_image_url  # 用户选择的角色图片URL
        print(f"[API] 初始化故事请求: thread_id={request.thread_id}, character_id={character_id}, scene_id={scene_id}, character_image_url={character_image_url}")
        result = game_service.initialize_story(request.thread_id, character_id, scene_id, character_image_url)
        print(f"[API] 初始化故事成功")
        return success_response(data=result)
    except ValueError as e:
        print(f"[API错误] 参数错误: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return error_response(code=400, message=f"参数错误: {str(e)}")
    except Exception as e:
        print(f"[API错误] 初始化故事失败: {str(e)}")
        import traceback
        error_trace = traceback.format_exc()
        print(error_trace)
        return error_response(code=500, message=f"初始化故事失败: {str(e)}", error={"traceback": error_trace})

