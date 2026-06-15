"""后台预生成器（异步生成场景图片）"""
import os
import sys
import time
import threading
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from utils.logger import get_logger
from api.services.image.image_generation_service import ImageGenerationService
from api.services.image.image_pool_service import ImagePoolService, MIN_POOL_SIZE
from api.services.image.image_storage_service import ImageStorageService
from data.scenes import SUB_SCENES

logger = get_logger(__name__)

# 配置常量
MAX_WORKERS = 2  # 最大并发生成数
CHECK_INTERVAL = 60  # 检查间隔（秒）
GENERATION_TIMEOUT = 300  # 单次生成超时（秒）


class BackgroundGenerator:
    """后台预生成器
    
    职责：
    - 监控图片池状态
    - 当池低于 MIN_POOL_SIZE 时自动触发异步生成
    - 管理生成任务队列
    """
    
    def __init__(self, 
                 generation_service: Optional[ImageGenerationService] = None,
                 pool_service: Optional[ImagePoolService] = None,
                 storage_service: Optional[ImageStorageService] = None):
        """初始化后台预生成器
        
        Args:
            generation_service: 图片生成服务（可选）
            pool_service: 图片池服务（可选）
            storage_service: 图片存储服务（可选）
        """
        self.generation_service = generation_service or ImageGenerationService()
        self.pool_service = pool_service or ImagePoolService()
        self.storage_service = storage_service or ImageStorageService()
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        self.running = False
        self.check_thread = None
        
        # 任务跟踪
        self.pending_futures: Dict[str, Future] = {}
        self.generation_stats = {
            'total_generated': 0,
            'total_failed': 0,
            'last_check_time': None,
            'last_generation_time': None
        }
        
        # 锁
        self._lock = threading.Lock()
        
        logger.info("后台预生成器已初始化")
    
    def start(self) -> None:
        """启动后台预生成器"""
        if self.running:
            logger.warning("后台预生成器已在运行")
            return
        
        self.running = True
        self.check_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.check_thread.start()
        
        logger.info("后台预生成器已启动")
    
    def stop(self) -> None:
        """停止后台预生成器"""
        self.running = False
        
        if self.check_thread:
            self.check_thread.join(timeout=5)
        
        # 取消所有待处理的任务
        with self._lock:
            for future in self.pending_futures.values():
                future.cancel()
            self.pending_futures.clear()
        
        # 关闭线程池
        self.executor.shutdown(wait=False)
        
        logger.info("后台预生成器已停止")
    
    def trigger_generation(self, scene_id: str, count: int = 1) -> bool:
        """手动触发图片生成
        
        Args:
            scene_id: 场景ID
            count: 生成数量
            
        Returns:
            是否成功触发
        """
        try:
            if not self.generation_service.enabled:
                logger.warning("图片生成服务不可用，无法触发生成")
                return False
            
            # 检查是否已有该场景的生成任务
            with self._lock:
                if scene_id in self.pending_futures:
                    future = self.pending_futures[scene_id]
                    if not future.done():
                        logger.info(f"场景 {scene_id} 已有生成任务在进行中")
                        return True
            
            # 提交生成任务
            future = self.executor.submit(
                self._generate_images_for_scene,
                scene_id,
                count
            )
            
            with self._lock:
                self.pending_futures[scene_id] = future
            
            # 添加完成回调
            future.add_done_callback(
                lambda f, sid=scene_id: self._on_generation_complete(sid, f)
            )
            
            logger.info(f"已触发场景 {scene_id} 的图片生成任务，数量: {count}")
            
            return True
            
        except Exception as e:
            logger.error(f"触发图片生成失败: {e}", exc_info=True)
            return False
    
    def pregenerate_top_scenes(self, top_n: int = 20) -> Dict[str, Any]:
        """预生成高频场景的图片
        
        Args:
            top_n: 预生成的场景数量
            
        Returns:
            预生成结果
        """
        try:
            if not self.generation_service.enabled:
                return {
                    'success': False,
                    'message': '图片生成服务不可用'
                }
            
            # 获取所有场景
            all_scenes = list(SUB_SCENES.keys())
            
            # 选择前N个场景
            scenes_to_generate = all_scenes[:top_n]
            
            results = {
                'total_scenes': len(scenes_to_generate),
                'triggered': 0,
                'skipped': 0,
                'failed': 0
            }
            
            for scene_id in scenes_to_generate:
                # 检查池状态
                stats = self.pool_service.get_pool_stats(scene_id)
                
                if stats.get('high_quality_images', 0) >= MIN_POOL_SIZE:
                    results['skipped'] += 1
                    continue
                
                # 触发生成
                if self.trigger_generation(scene_id, count=MIN_POOL_SIZE):
                    results['triggered'] += 1
                else:
                    results['failed'] += 1
                
                # 避免过快触发
                time.sleep(0.1)
            
            return {
                'success': True,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"预生成高频场景失败: {e}", exc_info=True)
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_generation_status(self) -> Dict[str, Any]:
        """获取生成状态
        
        Returns:
            状态信息字典
        """
        with self._lock:
            pending_count = sum(
                1 for f in self.pending_futures.values() 
                if not f.done()
            )
        
        return {
            'running': self.running,
            'pending_tasks': pending_count,
            'stats': self.generation_stats.copy()
        }
    
    def _monitor_loop(self) -> None:
        """监控循环"""
        logger.info("开始监控图片池状态")
        
        while self.running:
            try:
                self.generation_stats['last_check_time'] = datetime.utcnow().isoformat()
                
                # 获取需要生成图片的场景
                scenes_needing_generation = self.pool_service.get_scenes_needing_generation()
                
                if scenes_needing_generation:
                    logger.info(f"发现 {len(scenes_needing_generation)} 个场景需要补充图片")
                    
                    # 为每个场景触发生成
                    for scene_id in scenes_needing_generation:
                        if not self.running:
                            break
                        
                        # 检查是否已有任务在进行
                        with self._lock:
                            if scene_id in self.pending_futures:
                                future = self.pending_futures[scene_id]
                                if not future.done():
                                    continue
                        
                        # 触发生成
                        self.trigger_generation(scene_id, count=1)
                        
                        # 避免过快触发
                        time.sleep(1)
                
                # 等待下一次检查
                for _ in range(CHECK_INTERVAL):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"监控循环异常: {e}", exc_info=True)
                time.sleep(10)
    
    def _generate_images_for_scene(self, scene_id: str, count: int) -> List[Dict[str, Any]]:
        """为指定场景生成图片
        
        Args:
            scene_id: 场景ID
            count: 生成数量
            
        Returns:
            生成的图片信息列表
        """
        generated_images = []
        
        try:
            # 获取场景信息
            scene_info = SUB_SCENES.get(scene_id, {})
            scene_name = scene_info.get('name', scene_id)
            
            for i in range(count):
                if not self.running:
                    break
                
                try:
                    # 生成场景图片prompt
                    scene_data = {
                        'scene_id': scene_id,
                        'scene_name': scene_name,
                        'scene_description': scene_info.get('description', '')
                    }
                    
                    prompt = self.generation_service.generate_scene_image_prompt(scene_data)
                    
                    # 生成图片
                    image_url = self.generation_service.generate_scene_image(
                        scene_data=scene_data,
                        scene_id=scene_id,
                        user_id='SYSTEM'  # 系统预生成
                    )
                    
                    if image_url:
                        # 保存图片到本地
                        image_path = self.storage_service.save_image(
                            image_url=image_url,
                            scene_id=scene_id,
                            scene_name=scene_name,
                            image_type='scene'
                        )
                        
                        # 添加到图片池
                        scene_image = self.pool_service.add_image_to_pool(
                            scene_id=scene_id,
                            image_url=image_url,
                            image_path=image_path,
                            quality_score=3.0,  # 默认质量分数
                            prompt_used=prompt,
                            metadata={
                                'generation_type': 'background',
                                'generated_at': datetime.utcnow().isoformat()
                            }
                        )
                        
                        if scene_image:
                            generated_images.append(scene_image.to_dict())
                            self.generation_stats['total_generated'] += 1
                            self.generation_stats['last_generation_time'] = datetime.utcnow().isoformat()
                            
                            logger.info(f"成功生成场景图片: scene_id={scene_id}, image_id={scene_image.id}")
                        else:
                            self.generation_stats['total_failed'] += 1
                            logger.warning(f"添加图片到池失败: scene_id={scene_id}")
                    else:
                        self.generation_stats['total_failed'] += 1
                        logger.warning(f"生成场景图片失败: scene_id={scene_id}")
                    
                    # 生成间隔
                    if i < count - 1:
                        time.sleep(2)
                        
                except Exception as e:
                    self.generation_stats['total_failed'] += 1
                    logger.error(f"生成单张图片失败: {e}", exc_info=True)
                    continue
            
            return generated_images
            
        except Exception as e:
            logger.error(f"为场景生成图片失败: {e}", exc_info=True)
            return generated_images
    
    def _on_generation_complete(self, scene_id: str, future: Future) -> None:
        """生成完成回调
        
        Args:
            scene_id: 场景ID
            future: Future对象
        """
        try:
            with self._lock:
                if scene_id in self.pending_futures:
                    del self.pending_futures[scene_id]
            
            if future.exception():
                logger.error(f"场景 {scene_id} 的图片生成任务失败: {future.exception()}")
            else:
                result = future.result()
                logger.info(f"场景 {scene_id} 的图片生成任务完成，生成 {len(result)} 张图片")
                
        except Exception as e:
            logger.error(f"处理生成完成回调失败: {e}", exc_info=True)