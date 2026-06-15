"""LRU 内存缓存（减少磁盘IO）"""
import os
import sys
import time
import threading
from typing import Optional, Dict, Any, Tuple
from collections import OrderedDict
from datetime import datetime, timedelta

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from utils.logger import get_logger

logger = get_logger(__name__)

# 配置常量
CACHE_SIZE = int(os.getenv('IMAGE_CACHE_SIZE', '50'))
CACHE_TTL = 3600  # 缓存过期时间（秒）


class ImageCache:
    """LRU 内存缓存
    
    职责：
    - 缓存最近访问的图片
    - 减少磁盘IO
    - 自动过期清理
    """
    
    def __init__(self, max_size: int = CACHE_SIZE, ttl: int = CACHE_TTL):
        """初始化图片缓存
        
        Args:
            max_size: 最大缓存数量
            ttl: 缓存过期时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        
        # 使用 OrderedDict 实现 LRU
        self._cache: OrderedDict[str, Tuple[Dict[str, Any], float]] = OrderedDict()
        self._lock = threading.RLock()
        
        # 统计信息
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0
        }
        
        logger.info(f"图片缓存已初始化，最大容量: {max_size}，TTL: {ttl}秒")
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """获取缓存的图片信息
        
        Args:
            key: 缓存键（通常是 scene_id 或 image_id）
            
        Returns:
            图片信息字典，如果不存在或已过期返回None
        """
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            # 获取缓存项和时间戳
            value, timestamp = self._cache[key]
            
            # 检查是否过期
            if time.time() - timestamp > self.ttl:
                # 已过期，删除
                del self._cache[key]
                self._stats['expirations'] += 1
                self._stats['misses'] += 1
                logger.debug(f"缓存已过期: {key}")
                return None
            
            # 移动到末尾（最近使用）
            self._cache.move_to_end(key)
            self._stats['hits'] += 1
            
            logger.debug(f"缓存命中: {key}")
            return value
    
    def put(self, key: str, value: Dict[str, Any]) -> None:
        """添加图片到缓存
        
        Args:
            key: 缓存键
            value: 图片信息字典
        """
        with self._lock:
            # 如果已存在，更新并移动到末尾
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = (value, time.time())
                logger.debug(f"更新缓存: {key}")
                return
            
            # 如果缓存已满，删除最旧的项
            while len(self._cache) >= self.max_size:
                evicted_key, _ = self._cache.popitem(last=False)
                self._stats['evictions'] += 1
                logger.debug(f"驱逐缓存: {evicted_key}")
            
            # 添加新项
            self._cache[key] = (value, time.time())
            logger.debug(f"添加缓存: {key}")
    
    def remove(self, key: str) -> bool:
        """从缓存中删除图片
        
        Args:
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"删除缓存: {key}")
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            logger.info("缓存已清空")
    
    def cleanup_expired(self) -> int:
        """清理过期的缓存项
        
        Returns:
            清理的数量
        """
        with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for key, (value, timestamp) in self._cache.items():
                if current_time - timestamp > self.ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                self._stats['expirations'] += 1
            
            if expired_keys:
                logger.info(f"清理了 {len(expired_keys)} 个过期缓存")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'ttl': self.ttl,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': round(hit_rate, 2),
                'evictions': self._stats['evictions'],
                'expirations': self._stats['expirations']
            }
    
    def get_or_load(self, key: str, loader_func) -> Optional[Dict[str, Any]]:
        """获取缓存或加载数据
        
        Args:
            key: 缓存键
            loader_func: 加载函数（返回图片信息字典）
            
        Returns:
            图片信息字典
        """
        # 尝试从缓存获取
        value = self.get(key)
        if value is not None:
            return value
        
        # 缓存未命中，加载数据
        try:
            value = loader_func()
            if value is not None:
                self.put(key, value)
            return value
        except Exception as e:
            logger.error(f"加载数据失败: {e}", exc_info=True)
            return None
    
    def keys(self) -> list:
        """获取所有缓存键
        
        Returns:
            缓存键列表
        """
        with self._lock:
            return list(self._cache.keys())
    
    def values(self) -> list:
        """获取所有缓存值
        
        Returns:
            缓存值列表
        """
        with self._lock:
            return [value for value, _ in self._cache.values()]
    
    def items(self) -> list:
        """获取所有缓存项
        
        Returns:
            缓存项列表（键值对）
        """
        with self._lock:
            return [(key, value) for key, (value, _) in self._cache.items()]
    
    def __len__(self) -> int:
        """获取缓存大小"""
        with self._lock:
            return len(self._cache)
    
    def __contains__(self, key: str) -> bool:
        """检查键是否在缓存中"""
        with self._lock:
            if key not in self._cache:
                return False
            
            # 检查是否过期
            _, timestamp = self._cache[key]
            if time.time() - timestamp > self.ttl:
                del self._cache[key]
                return False
            
            return True
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"<ImageCache(size={len(self._cache)}, max_size={self.max_size})>"