"""场景图片管理端点"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime
from api.services.image.image_pool_service import ImagePoolService
from api.services.image.background_generator import BackgroundGenerator
from api.services.image.image_generation_service import ImageGenerationService
from api.services.image.image_storage_service import ImageStorageService
from api.services.image.image_cache import ImageCache
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/v1/admin/scenes", tags=["场景图片管理"])

# 初始化服务
image_generation_service = ImageGenerationService()
image_storage_service = ImageStorageService()
image_pool_service = ImagePoolService()
background_generator = BackgroundGenerator(
    generation_service=image_generation_service,
    pool_service=image_pool_service,
    storage_service=image_storage_service
)
image_cache = ImageCache()


@router.get("/pool-stats")
async def get_pool_stats(scene_id: Optional[str] = Query(None, description="场景ID（可选）")):
    """
    获取场景图片池统计信息
    
    Args:
        scene_id: 场景ID（可选，如果不提供则返回所有场景的统计）
        
    Returns:
        dict: 图片池统计信息
    """
    try:
        stats = image_pool_service.get_pool_stats(scene_id)
        
        return {
            "code": 200,
            "message": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取图片池统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取图片池统计失败")


@router.post("/pre-generate")
async def pre_generate_scenes(
    scene_id: Optional[str] = Query(None, description="场景ID（可选）"),
    count: int = Query(1, description="每个场景生成的图片数量"),
    top_n: int = Query(20, description="预生成的高频场景数量")
):
    """
    预生成场景图片
    
    Args:
        scene_id: 场景ID（可选，如果不提供则预生成高频场景）
        count: 每个场景生成的图片数量
        top_n: 预生成的高频场景数量
        
    Returns:
        dict: 预生成结果
    """
    try:
        if not image_generation_service.enabled:
            raise HTTPException(
                status_code=400, 
                detail="图片生成服务不可用，请配置VOLCENGINE_ARK_API_KEY或DASHSCOPE_API_KEY"
            )
        
        if scene_id:
            # 为指定场景生成图片
            success = background_generator.trigger_generation(scene_id, count)
            
            if success:
                return {
                    "code": 200,
                    "message": "success",
                    "data": {
                        "scene_id": scene_id,
                        "count": count,
                        "status": "generation_triggered"
                    }
                }
            else:
                raise HTTPException(status_code=400, detail="触发图片生成失败")
        else:
            # 预生成高频场景
            result = background_generator.pregenerate_top_scenes(top_n)
            
            if result['success']:
                return {
                    "code": 200,
                    "message": "success",
                    "data": result['results']
                }
            else:
                raise HTTPException(status_code=400, detail=result['message'])
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预生成场景图片失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="预生成场景图片失败")


@router.get("/generation-status")
async def get_generation_status():
    """
    获取图片生成状态
    
    Returns:
        dict: 生成状态信息
    """
    try:
        status = background_generator.get_generation_status()
        
        return {
            "code": 200,
            "message": "success",
            "data": status
        }
    except Exception as e:
        logger.error(f"获取生成状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取生成状态失败")


@router.post("/start-background-generator")
async def start_background_generator():
    """
    启动后台预生成器
    
    Returns:
        dict: 操作结果
    """
    try:
        background_generator.start()
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "status": "started",
                "message": "后台预生成器已启动"
            }
        }
    except Exception as e:
        logger.error(f"启动后台预生成器失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="启动后台预生成器失败")


@router.post("/stop-background-generator")
async def stop_background_generator():
    """
    停止后台预生成器
    
    Returns:
        dict: 操作结果
    """
    try:
        background_generator.stop()
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "status": "stopped",
                "message": "后台预生成器已停止"
            }
        }
    except Exception as e:
        logger.error(f"停止后台预生成器失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="停止后台预生成器失败")


@router.get("/cache-stats")
async def get_cache_stats():
    """
    获取图片缓存统计信息
    
    Returns:
        dict: 缓存统计信息
    """
    try:
        stats = image_cache.get_stats()
        
        return {
            "code": 200,
            "message": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取缓存统计失败")


@router.post("/clear-cache")
async def clear_cache():
    """
    清空图片缓存
    
    Returns:
        dict: 操作结果
    """
    try:
        image_cache.clear()
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "status": "cleared",
                "message": "图片缓存已清空"
            }
        }
    except Exception as e:
        logger.error(f"清空缓存失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="清空缓存失败")


@router.get("/random-image")
async def get_random_scene_image(scene_id: str = Query(..., description="场景ID")):
    """
    从场景图片池中随机获取一张图片
    
    Args:
        scene_id: 场景ID
        
    Returns:
        dict: 图片信息
    """
    try:
        # 尝试从缓存获取
        cache_key = f"random_image:{scene_id}"
        cached_image = image_cache.get(cache_key)
        
        if cached_image:
            return {
                "code": 200,
                "message": "success",
                "data": {
                    "image": cached_image,
                    "source": "cache"
                }
            }
        
        # 从图片池获取
        image = image_pool_service.get_random_image(scene_id)
        
        if image:
            # 添加到缓存
            image_cache.put(cache_key, image)
            
            return {
                "code": 200,
                "message": "success",
                "data": {
                    "image": image,
                    "source": "pool"
                }
            }
        else:
            raise HTTPException(status_code=404, detail=f"场景 {scene_id} 没有可用的图片")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取随机场景图片失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取随机场景图片失败")