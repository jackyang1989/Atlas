import psutil
import logging
from typing import Dict
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.user import User

logger = logging.getLogger(__name__)


class MonitorManager:
    """系统监控管理类"""
    
    @staticmethod
    def get_cpu_stats() -> Dict:
        """获取 CPU 统计信息"""
        return {
            "usage_percent": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count(),
            "count_logical": psutil.cpu_count(logical=True),
        }
    
    @staticmethod
    def get_memory_stats() -> Dict:
        """获取内存统计信息"""
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024 ** 3), 2),
            "available_gb": round(mem.available / (1024 ** 3), 2),
            "used_gb": round(mem.used / (1024 ** 3), 2),
            "percent": mem.percent,
        }
    
    @staticmethod
    def get_disk_stats() -> Dict:
        """获取磁盘统计信息"""
        disk = psutil.disk_usage('/')
        return {
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "used_gb": round(disk.used / (1024 ** 3), 2),
            "free_gb": round(disk.free / (1024 ** 3), 2),
            "percent": disk.percent,
        }
    
    @staticmethod
    def get_network_stats() -> Dict:
        """获取网络统计信息"""
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent_gb": round(net_io.bytes_sent / (1024 ** 3), 2),
            "bytes_recv_gb": round(net_io.bytes_recv / (1024 ** 3), 2),
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errin": net_io.errin,
            "errout": net_io.errout,
        }
    
    @staticmethod
    def get_process_stats() -> Dict:
        """获取进程统计信息"""
        return {
            "total_processes": len(psutil.pids()),
            "process_count": psutil.Process().num_threads(),
        }
    
    @staticmethod
    def get_uptime_stats() -> Dict:
        """获取系统运行时间"""
        import time
        uptime_seconds = time.time() - psutil.boot_time()
        
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        return {
            "uptime_seconds": int(uptime_seconds),
            "uptime_days": days,
            "uptime_hours": hours,
            "uptime_minutes": minutes,
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
        }
    
    @staticmethod
    def get_system_stats() -> Dict:
        """获取完整系统统计信息"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": MonitorManager.get_cpu_stats(),
            "memory": MonitorManager.get_memory_stats(),
            "disk": MonitorManager.get_disk_stats(),
            "network": MonitorManager.get_network_stats(),
            "process": MonitorManager.get_process_stats(),
            "uptime": MonitorManager.get_uptime_stats(),
        }
    
    @staticmethod
    def get_dashboard_stats(db: Session) -> Dict:
        """获取仪表盘统计信息"""
        # 基础统计
        total_services = db.query(Service).count()
        running_services = db.query(Service).filter(Service.status == "running").count()
        
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.status == "active").count()
        
        # 流量统计
        total_traffic_used = db.query(User).with_entities(
            db.func.sum(User.traffic_used_gb)
        ).scalar() or 0
        
        total_traffic_limit = db.query(User).with_entities(
            db.func.sum(User.traffic_limit_gb)
        ).scalar() or 0
        
        # 用户状态分布
        user_status_dist = {}
        for status in ['active', 'disabled', 'expired', 'over_quota']:
            count = db.query(User).filter(User.status == status).count()
            user_status_dist[status] = count
        
        # 系统统计
        system_stats = MonitorManager.get_system_stats()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "total": total_services,
                "running": running_services,
                "stopped": total_services - running_services,
            },
            "users": {
                "total": total_users,
                "active": active_users,
                "distribution": user_status_dist,
            },
            "traffic": {
                "used_gb": round(total_traffic_used, 2),
                "limit_gb": round(total_traffic_limit, 2),
                "usage_percent": round(
                    (total_traffic_used / total_traffic_limit * 100) 
                    if total_traffic_limit > 0 else 0, 
                    2
                ),
            },
            "system": system_stats,
        }
    
    @staticmethod
    def health_check() -> Dict:
        """系统健康检查"""
        cpu_percent = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 定义告警阈值
        cpu_warning = cpu_percent > 80
        mem_warning = mem.percent > 80
        disk_warning = disk.percent > 80
        
        status = "ok"
        if cpu_warning or mem_warning or disk_warning:
            status = "warning"
        
        return {
            "status": status,
            "cpu_percent": cpu_percent,
            "memory_percent": mem.percent,
            "disk_percent": disk.percent,
            "warnings": {
                "cpu": cpu_warning,
                "memory": mem_warning,
                "disk": disk_warning,
            }
        }
