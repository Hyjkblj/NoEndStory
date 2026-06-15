"""安全服务层"""
import time
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from utils.logger import setup_logger
import os

logger = setup_logger(__name__)


class SecurityService:
    """
    安全服务
    
    功能：
    1. IP封禁管理（自动检测 + 手动封禁）
    2. 游客行为监控
    3. 审计日志记录
    4. 安全统计
    """
    
    def __init__(self):
        """初始化安全服务"""
        # IP封禁记录 {ip: {'banned_until': timestamp, 'reason': str, 'banned_at': timestamp}}
        self.banned_ips: Dict[str, Dict] = {}
        
        # IP行为记录 {ip: {'guest_visits': [(timestamp, endpoint), ...], 'total_requests': int}}
        self.ip_behavior: Dict[str, Dict] = {}
        
        self._lock = asyncio.Lock()
        
        # 自动封禁阈值配置
        self.auto_ban_thresholds = {
            'hourly_guest_visits': 5,  # 1小时内游客访问次数
            'hourly_ban_duration': 3600,  # 封禁时长（秒）- 1小时
            'daily_guest_visits': 10,  # 24小时内游客访问次数
            'daily_ban_duration': 86400,  # 封禁时长（秒）- 24小时
        }
        
        # 审计日志
        self.audit_logs: List[Dict] = []
        
        logger.info("安全服务初始化完成")
    
    async def is_ip_banned(self, ip: str) -> Tuple[bool, Optional[Dict]]:
        """
        检查IP是否被封禁
        
        Args:
            ip: 客户端IP
            
        Returns:
            Tuple[bool, Optional[Dict]]: (是否被封禁, 封禁信息)
        """
        async with self._lock:
            if ip not in self.banned_ips:
                return False, None
            
            ban_info = self.banned_ips[ip]
            banned_until = ban_info.get('banned_until')
            
            # 检查封禁是否过期
            if banned_until and time.time() > banned_until:
                # 封禁已过期，移除
                del self.banned_ips[ip]
                logger.info(f"IP封禁已过期并移除: {ip}")
                return False, None
            
            return True, ban_info
    
    async def ban_ip(self, ip: str, reason: str, duration_seconds: int = None, permanent: bool = False):
        """
        封禁IP
        
        Args:
            ip: 客户端IP
            reason: 封禁原因
            duration_seconds: 封禁时长（秒），permanent为True时忽略
            permanent: 是否永久封禁
        """
        async with self._lock:
            current_time = time.time()
            
            if permanent:
                banned_until = None
            else:
                banned_until = current_time + (duration_seconds or self.auto_ban_thresholds['hourly_ban_duration'])
            
            self.banned_ips[ip] = {
                'banned_until': banned_until,
                'reason': reason,
                'banned_at': current_time,
                'permanent': permanent
            }
            
            # 记录审计日志
            await self._add_audit_log(
                action="ip_banned",
                ip=ip,
                details={
                    'reason': reason,
                    'duration_seconds': duration_seconds,
                    'permanent': permanent,
                    'banned_until': banned_until
                }
            )
            
            logger.warning(f"IP已封禁: {ip}, 原因: {reason}, 永久: {permanent}")
    
    async def unban_ip(self, ip: str) -> bool:
        """
        解封IP
        
        Args:
            ip: 客户端IP
            
        Returns:
            bool: 是否成功解封
        """
        async with self._lock:
            if ip in self.banned_ips:
                del self.banned_ips[ip]
                
                # 记录审计日志
                await self._add_audit_log(
                    action="ip_unbanned",
                    ip=ip,
                    details={}
                )
                
                logger.info(f"IP已解封: {ip}")
                return True
            
            return False
    
    async def record_guest_visit(self, ip: str, endpoint: str):
        """
        记录游客访问
        
        Args:
            ip: 客户端IP
            endpoint: 访问的端点
        """
        async with self._lock:
            current_time = time.time()
            
            if ip not in self.ip_behavior:
                self.ip_behavior[ip] = {
                    'guest_visits': [],
                    'total_requests': 0
                }
            
            behavior = self.ip_behavior[ip]
            
            # 记录访问
            behavior['guest_visits'].append((current_time, endpoint))
            behavior['total_requests'] += 1
            
            # 清理旧记录（保留24小时）
            cutoff_time = current_time - 86400
            behavior['guest_visits'] = [
                (ts, ep) for ts, ep in behavior['guest_visits']
                if ts > cutoff_time
            ]
            
            # 检查是否需要自动封禁
            await self._check_auto_ban(ip, behavior)
    
    async def _check_auto_ban(self, ip: str, behavior: Dict):
        """
        检查是否需要自动封禁
        
        Args:
            ip: 客户端IP
            behavior: IP行为记录
        """
        current_time = time.time()
        hourly_cutoff = current_time - 3600
        daily_cutoff = current_time - 86400
        
        # 统计1小时内游客访问次数
        hourly_visits = sum(1 for ts, _ in behavior['guest_visits'] if ts > hourly_cutoff)
        
        # 统计24小时内游客访问次数
        daily_visits = sum(1 for ts, _ in behavior['guest_visits'] if ts > daily_cutoff)
        
        # 检查小时阈值
        if hourly_visits >= self.auto_ban_thresholds['hourly_guest_visits']:
            await self.ban_ip(
                ip=ip,
                reason=f"1小时内游客访问次数过多 ({hourly_visits}次)",
                duration_seconds=self.auto_ban_thresholds['hourly_ban_duration']
            )
            return
        
        # 检查日阈值
        if daily_visits >= self.auto_ban_thresholds['daily_guest_visits']:
            await self.ban_ip(
                ip=ip,
                reason=f"24小时内游客访问次数过多 ({daily_visits}次)",
                duration_seconds=self.auto_ban_thresholds['daily_ban_duration']
            )
    
    async def _add_audit_log(self, action: str, ip: str = None, details: Dict = None):
        """
        添加审计日志
        
        Args:
            action: 操作类型
            ip: 客户端IP
            details: 详细信息
        """
        log_entry = {
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
            'action': action,
            'ip': ip,
            'details': details or {}
        }
        
        self.audit_logs.append(log_entry)
        
        # 限制审计日志数量（保留最近10000条）
        if len(self.audit_logs) > 10000:
            self.audit_logs = self.audit_logs[-10000:]
    
    async def get_banned_ips(self) -> List[Dict]:
        """
        获取所有被封禁的IP
        
        Returns:
            List[Dict]: 封禁IP列表
        """
        async with self._lock:
            current_time = time.time()
            result = []
            
            for ip, ban_info in self.banned_ips.items():
                # 检查封禁是否过期
                banned_until = ban_info.get('banned_until')
                if banned_until and current_time > banned_until:
                    continue
                
                result.append({
                    'ip': ip,
                    'reason': ban_info.get('reason'),
                    'banned_at': ban_info.get('banned_at'),
                    'banned_until': banned_until,
                    'permanent': ban_info.get('permanent', False)
                })
            
            return result
    
    async def get_ip_behavior(self, ip: str) -> Optional[Dict]:
        """
        获取IP行为记录
        
        Args:
            ip: 客户端IP
            
        Returns:
            Optional[Dict]: IP行为记录
        """
        async with self._lock:
            if ip not in self.ip_behavior:
                return None
            
            behavior = self.ip_behavior[ip]
            current_time = time.time()
            
            # 统计各时间段访问次数
            hourly_visits = sum(1 for ts, _ in behavior['guest_visits'] if ts > current_time - 3600)
            daily_visits = sum(1 for ts, _ in behavior['guest_visits'] if ts > current_time - 86400)
            
            return {
                'ip': ip,
                'hourly_guest_visits': hourly_visits,
                'daily_guest_visits': daily_visits,
                'total_requests': behavior['total_requests'],
                'last_visit': behavior['guest_visits'][-1][0] if behavior['guest_visits'] else None
            }
    
    async def get_audit_logs(self, limit: int = 100, action: str = None) -> List[Dict]:
        """
        获取审计日志
        
        Args:
            limit: 返回数量限制
            action: 过滤操作类型
            
        Returns:
            List[Dict]: 审计日志列表
        """
        async with self._lock:
            logs = self.audit_logs
            
            # 过滤操作类型
            if action:
                logs = [log for log in logs if log['action'] == action]
            
            # 返回最近的日志
            return logs[-limit:]
    
    async def get_stats(self) -> Dict:
        """
        获取安全统计
        
        Returns:
            Dict: 统计信息
        """
        async with self._lock:
            current_time = time.time()
            
            # 统计被封禁的IP数量
            active_bans = 0
            for ban_info in self.banned_ips.values():
                banned_until = ban_info.get('banned_until')
                if not banned_until or current_time <= banned_until:
                    active_bans += 1
            
            # 统计审计日志
            hourly_logs = sum(1 for log in self.audit_logs if log['timestamp'] > current_time - 3600)
            daily_logs = sum(1 for log in self.audit_logs if log['timestamp'] > current_time - 86400)
            
            return {
                'active_bans': active_bans,
                'total_ips_tracked': len(self.ip_behavior),
                'hourly_audit_events': hourly_logs,
                'daily_audit_events': daily_logs,
                'total_audit_logs': len(self.audit_logs)
            }


# 创建安全服务实例
security_service = SecurityService()