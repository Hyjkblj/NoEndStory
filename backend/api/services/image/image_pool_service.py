"""场景图片池服务（加权随机抽取 + 池大小管理）"""
import os
import sys
import random
from typing import Optional, List, Dict, Any
from datetime import datetime

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from utils.logger import get_logger
from models.scene_image import SceneImage
from database.db_manager import DatabaseManager
from sqlalchemy import func

logger = get_logger(__name__)

# 配置常量
MIN_POOL_SIZE = int(os.getenv('SCENE_IMAGE_MIN_POOL_SIZE', '5'))
MAX_POOL_SIZE = int(os.getenv('SCENE_IMAGE_MAX_POOL_SIZE', '10'))
MIN_QUALITY_SCORE = 3.0


class ImagePoolService:
    """场景图片池服务
    
    职责：
    - 从场景图片池中加权随机抽取图片
    - 管理池大小（5-10张/场景）
    - 低分图片淘汰
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """初始化图片池服务
        
        Args:
            db_manager: 数据库管理器（可选，如果不提供则创建新实例）
        """
        self.db_manager = db_manager or DatabaseManager()
    
    def get_random_image(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """从场景图片池中随机抽取一张图片

        使用加权随机抽取，权重基于质量分数。

        Args:
            scene_id: 场景ID

        Returns:
            图片信息字典，如果没有可用图片返回None
        """
        try:
            with self.db_manager.get_session() as session:
                images = session.query(SceneImage).filter(
                    SceneImage.scene_id == scene_id,
                    SceneImage.status == 'active',
                    SceneImage.quality_score >= MIN_QUALITY_SCORE
                ).all()

                if not images:
                    logger.warning(f"场景 {scene_id} 没有可用的图片")
                    return None

                # 加权随机抽取
                weights = [img.quality_score for img in images]
                selected_image = random.choices(images, weights=weights, k=1)[0]

                logger.debug(f"从场景 {scene_id} 的 {len(images)} 张图片中抽取: {selected_image.id}")

                return selected_image.to_dict()
        except Exception as e:
            logger.error(f"从图片池抽取图片失败: {e}", exc_info=True)
            return None
    
    def get_pool_stats(self, scene_id: Optional[str] = None) -> Dict[str, Any]:
        """获取图片池统计信息

        Args:
            scene_id: 场景ID（可选，如果不提供则返回所有场景的统计）

        Returns:
            统计信息字典
        """
        try:
            with self.db_manager.get_session() as session:
                if scene_id:
                    # 单个场景的统计
                    total = session.query(SceneImage).filter(
                        SceneImage.scene_id == scene_id
                    ).count()

                    active = session.query(SceneImage).filter(
                        SceneImage.scene_id == scene_id,
                        SceneImage.status == 'active'
                    ).count()

                    high_quality = session.query(SceneImage).filter(
                        SceneImage.scene_id == scene_id,
                        SceneImage.status == 'active',
                        SceneImage.quality_score >= MIN_QUALITY_SCORE
                    ).count()

                    avg_score = session.query(SceneImage).filter(
                        SceneImage.scene_id == scene_id,
                        SceneImage.status == 'active'
                    ).with_entities(
                        func.avg(SceneImage.quality_score)
                    ).scalar() or 0.0

                    return {
                        'scene_id': scene_id,
                        'total_images': total,
                        'active_images': active,
                        'high_quality_images': high_quality,
                        'average_quality_score': round(float(avg_score), 2),
                        'pool_status': 'healthy' if high_quality >= MIN_POOL_SIZE else 'low',
                        'needs_generation': high_quality < MIN_POOL_SIZE
                    }
                else:
                    # 所有场景的统计
                    stats = session.query(
                        SceneImage.scene_id,
                        func.count(SceneImage.id).label('total'),
                        func.count(SceneImage.id).filter(SceneImage.status == 'active').label('active'),
                        func.count(SceneImage.id).filter(
                            SceneImage.status == 'active',
                            SceneImage.quality_score >= MIN_QUALITY_SCORE
                        ).label('high_quality'),
                        func.avg(SceneImage.quality_score).filter(SceneImage.status == 'active').label('avg_score')
                    ).group_by(SceneImage.scene_id).all()

                    result = []
                    for stat in stats:
                        result.append({
                            'scene_id': stat.scene_id,
                            'total_images': stat.total,
                            'active_images': stat.active,
                            'high_quality_images': stat.high_quality,
                            'average_quality_score': round(float(stat.avg_score or 0), 2),
                            'pool_status': 'healthy' if stat.high_quality >= MIN_POOL_SIZE else 'low',
                            'needs_generation': stat.high_quality < MIN_POOL_SIZE
                        })

                    return {
                        'scenes': result,
                        'total_scenes': len(result),
                        'scenes_needing_generation': sum(1 for s in result if s['needs_generation'])
                    }
        except Exception as e:
            logger.error(f"获取图片池统计失败: {e}", exc_info=True)
            return {}
    
    def add_image_to_pool(self, scene_id: str, image_url: str,
                          image_path: Optional[str] = None,
                          quality_score: float = 3.0,
                          prompt_used: Optional[str] = None,
                          metadata: Optional[Dict] = None) -> Optional[SceneImage]:
        """添加图片到池中

        Args:
            scene_id: 场景ID
            image_url: 图片URL
            image_path: 图片本地路径（可选）
            quality_score: 质量分数（0-5）
            prompt_used: 使用的prompt（可选）
            metadata: 扩展元数据（可选）

        Returns:
            创建的SceneImage对象，如果失败返回None
        """
        try:
            with self.db_manager.get_session() as session:
                # 检查池大小，如果超过最大值则清理低分图片
                self._cleanup_pool_if_needed(session, scene_id)

                # 创建新的图片记录
                scene_image = SceneImage(
                    scene_id=scene_id,
                    image_url=image_url,
                    image_path=image_path,
                    quality_score=quality_score,
                    status='active',
                    prompt_used=prompt_used,
                    image_metadata=metadata,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )

                session.add(scene_image)

                logger.info(f"添加图片到池: scene_id={scene_id}, quality={quality_score}")

                return scene_image
        except Exception as e:
            logger.error(f"添加图片到池失败: {e}", exc_info=True)
            return None
    
    def update_image_quality(self, image_id: int, quality_score: float) -> bool:
        """更新图片质量分数

        Args:
            image_id: 图片ID
            quality_score: 新的质量分数（0-5）

        Returns:
            是否更新成功
        """
        try:
            with self.db_manager.get_session() as session:
                image = session.query(SceneImage).filter(SceneImage.id == image_id).first()
                if not image:
                    logger.warning(f"图片不存在: {image_id}")
                    return False

                image.quality_score = quality_score
                image.updated_at = datetime.utcnow()

                logger.debug(f"更新图片质量分数: {image_id} -> {quality_score}")

                return True
        except Exception as e:
            logger.error(f"更新图片质量分数失败: {e}", exc_info=True)
            return False
    
    def deactivate_image(self, image_id: int) -> bool:
        """停用图片

        Args:
            image_id: 图片ID

        Returns:
            是否停用成功
        """
        try:
            with self.db_manager.get_session() as session:
                image = session.query(SceneImage).filter(SceneImage.id == image_id).first()
                if not image:
                    logger.warning(f"图片不存在: {image_id}")
                    return False

                image.status = 'inactive'
                image.updated_at = datetime.utcnow()

                logger.debug(f"停用图片: {image_id}")

                return True
        except Exception as e:
            logger.error(f"停用图片失败: {e}", exc_info=True)
            return False
    
    def _cleanup_pool_if_needed(self, session, scene_id: str) -> None:
        """如果池超过最大值，清理低分图片
        
        Args:
            session: 数据库会话
            scene_id: 场景ID
        """
        try:
            from sqlalchemy import func
            
            # 获取当前池大小
            pool_size = session.query(SceneImage).filter(
                SceneImage.scene_id == scene_id,
                SceneImage.status == 'active'
            ).count()
            
            if pool_size < MAX_POOL_SIZE:
                return
            
            # 找到质量最低的图片
            lowest_quality_image = session.query(SceneImage).filter(
                SceneImage.scene_id == scene_id,
                SceneImage.status == 'active'
            ).order_by(SceneImage.quality_score.asc()).first()
            
            if lowest_quality_image:
                lowest_quality_image.status = 'inactive'
                lowest_quality_image.updated_at = datetime.utcnow()
                session.flush()
                
                logger.debug(f"清理低分图片: scene_id={scene_id}, image_id={lowest_quality_image.id}, "
                           f"quality={lowest_quality_image.quality_score}")
                
        except Exception as e:
            logger.warning(f"清理图片池失败: {e}", exc_info=True)
    
    def get_scenes_needing_generation(self) -> List[str]:
        """获取需要生成图片的场景列表

        Returns:
            需要生成图片的场景ID列表
        """
        try:
            with self.db_manager.get_session() as session:
                # 查询所有场景的高质量图片数量
                stats = session.query(
                    SceneImage.scene_id,
                    func.count(SceneImage.id).filter(
                        SceneImage.status == 'active',
                        SceneImage.quality_score >= MIN_QUALITY_SCORE
                    ).label('high_quality_count')
                ).group_by(SceneImage.scene_id).all()

                # 找出图片数量不足的场景
                scenes_needing_generation = []
                for stat in stats:
                    if stat.high_quality_count < MIN_POOL_SIZE:
                        scenes_needing_generation.append(stat.scene_id)

                return scenes_needing_generation
        except Exception as e:
            logger.error(f"获取需要生成图片的场景失败: {e}", exc_info=True)
            return []