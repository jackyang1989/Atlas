from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.admin import AdminUser
from app.schemas.component import (
    ComponentCreate,
    ComponentUpdate,
    ComponentResponse,
    ComponentListResponse,
    ComponentInstallRequest,
    ComponentVersionCheckResponse
)
from app.services.component_manager import ComponentManager
from app.utils.security import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> str:
    """获取当前登录用户"""
    token = credentials.credentials
    username = verify_token(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not admin:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return username


@router.get("/", response_model=ComponentListResponse)
async def list_components(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    type_filter: str = Query(None, description="组件类型过滤"),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """列出所有组件"""
    components, total = ComponentManager.list_components(
        db, 
        skip=skip, 
        limit=limit,
        type_filter=type_filter
    )
    return {
        "total": total,
        "items": components
    }


@router.post("/", response_model=ComponentResponse, status_code=status.HTTP_201_CREATED)
async def create_component(
    request: ComponentCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """注册新组件"""
    try:
        component = ComponentManager.create_component(
            db,
            name=request.name,
            type=request.type,
            version=request.version,
            install_method=request.install_method,
            install_url=request.install_url
        )
        return component
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建组件出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建组件失败"
        )


@router.get("/{component_id}", response_model=ComponentResponse)
async def get_component(
    component_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取组件详情"""
    component = ComponentManager.get_component(db, component_id)
    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组件不存在"
        )
    return component


@router.put("/{component_id}", response_model=ComponentResponse)
async def update_component(
    component_id: str,
    request: ComponentUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新组件信息"""
    component = ComponentManager.update_component(
        db,
        component_id,
        **request.model_dump(exclude_unset=True)
    )
    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组件不存在"
        )
    return component


@router.post("/{component_id}/install", response_model=ComponentResponse)
async def install_component(
    component_id: str,
    request: ComponentInstallRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """安装组件"""
    try:
        component = ComponentManager.install_component(db, component_id, force=request.force)
        if not component:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="组件不存在"
            )
        return component
    except Exception as e:
        logger.error(f"安装组件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"安装失败: {str(e)}"
        )


@router.post("/{component_id}/uninstall", response_model=ComponentResponse)
async def uninstall_component(
    component_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """卸载组件"""
    try:
        component = ComponentManager.uninstall_component(db, component_id)
        if not component:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="组件不存在"
            )
        return component
    except Exception as e:
        logger.error(f"卸载组件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"卸载失败: {str(e)}"
        )


@router.get("/{component_id}/check-update", response_model=ComponentVersionCheckResponse)
async def check_component_update(
    component_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """检查组件更新"""
    try:
        result = ComponentManager.check_for_updates(db, component_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="组件不存在"
            )
        return result
    except Exception as e:
        logger.error(f"检查更新失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="检查更新失败"
        )


@router.post("/{component_id}/upgrade", response_model=ComponentResponse)
async def upgrade_component(
    component_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """升级组件到最新版本"""
    try:
        component = ComponentManager.upgrade_component(db, component_id)
        if not component:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="组件不存在或无可用更新"
            )
        return component
    except Exception as e:
        logger.error(f"升级组件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"升级失败: {str(e)}"
        )


@router.delete("/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_component(
    component_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除组件记录"""
    if not ComponentManager.delete_component(db, component_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组件不存在"
        )
    return None
