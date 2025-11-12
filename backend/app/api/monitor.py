from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.admin import AdminUser
from app.schemas.monitor import (
    SystemStatsResponse,
    DashboardStatsResponse,
    HealthCheckResponse,
)
from app.services.monitor_manager import MonitorManager
from app.utils.security import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> str:
    """获取并验证当前用户"""
    token = credentials.credentials
    username = verify_token(token)
    
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证用户是否存在
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return username


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: Session = Depends(get_db)):
    """系统健康检查（无需认证）"""
    try:
        return MonitorManager.health_check()
    except Exception as e:
        logger.error(f"健康检查出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="健康检查失败"
        )


@router.get("/system", response_model=SystemStatsResponse)
async def get_system_stats(
    current_user: str = Depends(get_current_user),
):
    """获取完整系统统计"""
    try:
        return MonitorManager.get_system_stats()
    except Exception as e:
        logger.error(f"获取系统统计出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取系统统计失败"
        )


@router.get("/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取仪表盘统计数据"""
    try:
        return MonitorManager.get_dashboard_stats(db)
    except Exception as e:
        logger.error(f"获取仪表盘统计出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取仪表盘统计失败"
        )


@router.get("/cpu")
async def get_cpu_stats(
    current_user: str = Depends(get_current_user),
):
    """获取 CPU 统计"""
    try:
        return MonitorManager.get_cpu_stats()
    except Exception as e:
        logger.error(f"获取 CPU 统计出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取 CPU 统计失败"
        )


@router.get("/memory")
async def get_memory_stats(
    current_user: str = Depends(get_current_user),
):
    """获取内存统计"""
    try:
        return MonitorManager.get_memory_stats()
    except Exception as e:
        logger.error(f"获取内存统计出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取内存统计失败"
        )


@router.get("/disk")
async def get_disk_stats(
    current_user: str = Depends(get_current_user),
):
    """获取磁盘统计"""
    try:
        return MonitorManager.get_disk_stats()
    except Exception as e:
        logger.error(f"获取磁盘统计出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取磁盘统计失败"
        )


@router.get("/network")
async def get_network_stats(
    current_user: str = Depends(get_current_user),
):
    """获取网络统计"""
    try:
        return MonitorManager.get_network_stats()
    except Exception as e:
        logger.error(f"获取网络统计出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取网络统计失败"
        )
