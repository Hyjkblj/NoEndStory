"""将现有文件系统中的场景图片注册到数据库

用法:
    python scripts/register_scene_images.py

功能:
    扫描 smallscenes/ 和 scenes/ 目录
    提取场景ID和中文名称
    注册到 scene_images 表
"""
import os
import sys
import re
from datetime import datetime

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config
from database.db_manager import DatabaseManager
from models.character import SceneImage
from data.scenes import SUB_SCENES
from utils.logger import setup_logger

logger = setup_logger(__name__)


def extract_scene_id_from_filename(filename: str) -> str:
    """从文件名提取场景ID

    支持的格式:
    - UNKNOWN_SCENE_{scene_id}_{scene_name}_scene_v1.jpg
    - {scene_id}_{scene_name}.jpg
    - {scene_id}.jpg
    """
    # 移除扩展名
    name = os.path.splitext(filename)[0]

    # 格式1: UNKNOWN_SCENE_{scene_id}_{scene_name}_scene_v1
    match = re.match(r'UNKNOWN_SCENE_(\w+?)_', name)
    if match:
        return match.group(1)

    # 格式2: {scene_id}_{scene_name}
    match = re.match(r'^(\w+?)_', name)
    if match:
        return match.group(1)

    # 格式3: {scene_id}
    return name


def find_scene_id_by_name(filename: str) -> str:
    """通过中文名称反查场景ID"""
    for scene_id, scene_info in SUB_SCENES.items():
        scene_name = scene_info.get('name', '')
        if scene_name and scene_name in filename:
            return scene_id
    return ''


def register_images_from_directory(directory: str, source_type: str, db_manager: DatabaseManager):
    """从目录注册图片到数据库

    Args:
        directory: 图片目录路径
        source_type: 来源类型 (smallscenes/scenes)
        db_manager: 数据库管理器
    """
    if not os.path.exists(directory):
        logger.warning(f"目录不存在: {directory}")
        return

    image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    registered_count = 0
    skipped_count = 0

    with db_manager.get_session() as session:
        for filename in os.listdir(directory):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in image_extensions:
                continue

            # 提取场景ID
            scene_id = extract_scene_id_from_filename(filename)

            # 如果提取失败，尝试通过中文名称反查
            if not scene_id or scene_id not in SUB_SCENES:
                scene_id = find_scene_id_by_name(filename)

            if not scene_id:
                logger.debug(f"无法识别场景ID，跳过: {filename}")
                skipped_count += 1
                continue

            # 构建URL
            from urllib.parse import quote
            encoded_filename = quote(filename, safe='')
            if source_type == 'smallscenes':
                image_url = f"/static/images/smallscenes/{encoded_filename}"
            else:
                image_url = f"/static/images/scenes/{encoded_filename}"

            image_path = os.path.join(directory, filename)

            # 检查是否已存在
            existing = session.query(SceneImage).filter(
                SceneImage.image_url == image_url
            ).first()

            if existing:
                logger.debug(f"已存在，跳过: {filename}")
                skipped_count += 1
                continue

            # 创建记录
            scene_image = SceneImage(
                scene_id=scene_id,
                image_url=image_url,
                image_path=image_path,
                quality_score=3.0,
                status='active',
                use_count=0,
                image_metadata={'source': 'filesystem_migration', 'original_filename': filename},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(scene_image)
            registered_count += 1
            logger.debug(f"注册: {scene_id} -> {filename}")

    logger.info(f"{source_type}: 注册 {registered_count} 张，跳过 {skipped_count} 张")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始注册场景图片到数据库")
    logger.info("=" * 60)

    db_manager = DatabaseManager()

    # 确保表存在
    SceneImage.__table__.create(db_manager.engine, checkfirst=True)

    # 注册 smallscenes 目录
    if hasattr(config, 'SMALL_SCENE_IMAGE_SAVE_DIR'):
        if os.path.isabs(config.SMALL_SCENE_IMAGE_SAVE_DIR):
            smallscenes_dir = config.SMALL_SCENE_IMAGE_SAVE_DIR
        else:
            smallscenes_dir = os.path.join(backend_dir, config.SMALL_SCENE_IMAGE_SAVE_DIR)
        logger.info(f"扫描 smallscenes 目录: {smallscenes_dir}")
        register_images_from_directory(smallscenes_dir, 'smallscenes', db_manager)

    # 注册 scenes 目录
    if hasattr(config, 'SCENE_IMAGE_SAVE_DIR'):
        if os.path.isabs(config.SCENE_IMAGE_SAVE_DIR):
            scenes_dir = config.SCENE_IMAGE_SAVE_DIR
        else:
            scenes_dir = os.path.join(backend_dir, config.SCENE_IMAGE_SAVE_DIR)
        logger.info(f"扫描 scenes 目录: {scenes_dir}")
        register_images_from_directory(scenes_dir, 'scenes', db_manager)

    # 统计结果
    with db_manager.get_session() as session:
        total = session.query(SceneImage).count()
        by_scene = session.query(
            SceneImage.scene_id,
            session.query(SceneImage).with_entities(SceneImage.scene_id).count()
        ).group_by(SceneImage.scene_id).all()

    logger.info("=" * 60)
    logger.info(f"注册完成！数据库中共有 {total} 张场景图片")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
