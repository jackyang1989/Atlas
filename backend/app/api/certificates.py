"""
证书管理 API 端点
文件：backend/app/api/certificates.py
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.admin import AdminUser
from app.models.domain import Domain
from app.schemas.certificate import (
    CertIssueRequest,
    CertRenewRequest,
    CertInfoResponse,
    CertProviderListResponse,
    AcmeStatusResponse,
)
from app.services.cert_manager import CertManager
from app.services.domain_manager import DomainManager
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


# ==================== acme.sh 管理 ====================

@router.get("/acme/status", response_model=AcmeStatusResponse)
async def get_acme_status(
    current_user: str = Depends(get_current_user),
):
    """获取 acme.sh 状态"""
    installed = CertManager.check_acme_installed()
    version = CertManager.get_acme_version() if installed else None
    
    return {
        "installed": installed,
        "version": version,
        "acme_path": CertManager.ACME_SH if installed else None,
    }


@router.post("/acme/install")
async def install_acme(
    current_user: str = Depends(get_current_user),
):
    """安装 acme.sh"""
    try:
        result = CertManager.install_acme()
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get('error', '安装失败')
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"安装 acme.sh 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"安装失败: {str(e)}"
        )


# ==================== DNS 提供商 ====================

@router.get("/providers", response_model=CertProviderListResponse)
async def list_providers(
    current_user: str = Depends(get_current_user),
):
    """获取支持的 DNS 提供商列表"""
    providers = CertManager.get_supported_providers()
    
    return {
        "total": len(providers),
        "providers": [
            {
                "id": key,
                "name": value['name'],
                "dns_type": value['dns_type'],
                "required_keys": value['required_keys'],
                "key_names": value['key_names'],
            }
            for key, value in providers.items()
        ]
    }


# ==================== 证书签发 ====================

@router.post("/issue")
async def issue_certificate(
    request: CertIssueRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """签发证书"""
    try:
        # 检查 acme.sh 是否已安装
        if not CertManager.check_acme_installed():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="acme.sh 未安装，请先安装"
            )
        
        # 获取域名信息
        domain_obj = DomainManager.get_domain_by_name(db, request.domain)
        if not domain_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="域名不存在"
            )
        
        # 根据模式签发证书
        if request.provider == 'standalone':
            result = CertManager.issue_cert_standalone(
                domain=request.domain,
                email=domain_obj.email,
            )
        else:
            # DNS API 模式
            if not request.api_credentials:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="DNS API 模式需要提供凭证"
                )
            
            result = CertManager.issue_cert_dns(
                domain=request.domain,
                email=domain_obj.email,
                provider=request.provider,
                api_credentials=request.api_credentials,
            )
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get('error', '签发失败')
            )
        
        # 更新域名的证书信息
        DomainManager.update_cert_info(
            db,
            domain_obj.id,
            cert_valid_from=result['valid_from'],
            cert_valid_to=result['valid_to']
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"签发证书失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"签发失败: {str(e)}"
        )


# ==================== 证书续期 ====================

@router.post("/renew")
async def renew_certificate(
    request: CertRenewRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """续期证书"""
    try:
        # 检查 acme.sh 是否已安装
        if not CertManager.check_acme_installed():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="acme.sh 未安装"
            )
        
        # 获取域名信息
        domain_obj = DomainManager.get_domain_by_name(db, request.domain)
        if not domain_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="域名不存在"
            )
        
        # 执行续期
        result = CertManager.renew_cert(
            domain=request.domain,
            provider=domain_obj.provider,
            api_credentials=request.api_credentials,
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get('error', '续期失败')
            )
        
        # 更新域名的证书信息
        DomainManager.update_cert_info(
            db,
            domain_obj.id,
            cert_valid_from=datetime.now(),
            cert_valid_to=result['valid_to']
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"续期证书失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"续期失败: {str(e)}"
        )


# ==================== 证书信息 ====================

@router.get("/info/{domain}", response_model=CertInfoResponse)
async def get_certificate_info(
    domain: str,
    current_user: str = Depends(get_current_user),
):
    """获取证书信息"""
    try:
        info = CertManager.get_cert_info(domain)
        
        if not info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="证书不存在"
            )
        
        return info
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取证书信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取证书信息失败"
        )


# ==================== 过期检查 ====================

@router.get("/check-expiring")
async def check_expiring_certificates(
    days: int = 30,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """检查即将过期的证书"""
    try:
        domains = CertManager.check_expiring_certs(db, days)
        
        return {
            "total": len(domains),
            "domains": [
                {
                    "domain": d.domain,
                    "cert_valid_to": d.cert_valid_to.isoformat() if d.cert_valid_to else None,
                    "days_remaining": (d.cert_valid_to - datetime.now()).days if d.cert_valid_to else None,
                }
                for d in domains
            ]
        }
    
    except Exception as e:
        logger.error(f"检查过期证书失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="检查失败"
        )
