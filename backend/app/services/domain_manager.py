import uuid
import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.domain import Domain

logger = logging.getLogger(__name__)


class DomainManager:
    """域名管理类"""
    
    @staticmethod
    def create_domain(
        db: Session,
        domain: str,
        email: str,
        provider: str = "standalone",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        auto_renew: bool = True,
        renew_before_days: int = 30,
    ) -> Domain:
        """创建新域名"""
        # 检查域名是否已存在
        existing = db.query(Domain).filter(Domain.domain == domain).first()
        if existing:
            raise ValueError(f"域名 {domain} 已存在")
        
        # 创建域名
        domain_obj = Domain(
            id=str(uuid.uuid4()),
            domain=domain,
            email=email,
            provider=provider,
            api_key=api_key,
            api_secret=api_secret,
            auto_renew=auto_renew,
            renew_before_days=renew_before_days,
        )
        
        db.add(domain_obj)
        db.commit()
        db.refresh(domain_obj)
        
        logger.info(f"✅ 域名创建成功: {domain}")
        return domain_obj
    
    @staticmethod
    def list_domains(
        db: Session,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[Domain], int]:
        """列出所有域名"""
        query = db.query(Domain)
        total = query.count()
        domains = query.offset(skip).limit(limit).all()
        return domains, total
    
    @staticmethod
    def get_domain(db: Session, domain_id: str) -> Optional[Domain]:
        """获取域名详情"""
        return db.query(Domain).filter(Domain.id == domain_id).first()
    
    @staticmethod
    def get_domain_by_name(db: Session, domain_name: str) -> Optional[Domain]:
        """按域名获取"""
        return db.query(Domain).filter(Domain.domain == domain_name).first()
    
    @staticmethod
    def update_domain(
        db: Session,
        domain_id: str,
        **kwargs
    ) -> Optional[Domain]:
        """更新域名"""
        domain = db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            return None
        
        # 更新允许的字段
        allowed_fields = [
            'email',
            'provider',
            'api_key',
            'api_secret',
            'auto_renew',
            'renew_before_days',
        ]
        
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(domain, key, value)
        
        domain.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(domain)
        logger.info(f"✅ 域名已更新: {domain.domain}")
        return domain
    
    @staticmethod
    def update_cert_info(
        db: Session,
        domain_id: str,
        cert_valid_from: datetime,
        cert_valid_to: datetime,
    ) -> Optional[Domain]:
        """更新证书信息"""
        domain = db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            return None
        
        domain.cert_valid_from = cert_valid_from
        domain.cert_valid_to = cert_valid_to
        domain.last_renew_at = datetime.utcnow()
        domain.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(domain)
        logger.info(f"✅ 证书信息已更新: {domain.domain}")
        return domain
    
    @staticmethod
    def check_expiring_domains(db: Session, days: int = 30) -> List[Domain]:
        """检查即将过期的域名"""
        now = datetime.utcnow()
        expiry_date = now + timedelta(days=days)
        
        domains = db.query(Domain).filter(
            Domain.cert_valid_to <= expiry_date,
            Domain.cert_valid_to > now,
            Domain.auto_renew == True,
        ).all()
        
        return domains
    
    @staticmethod
    def check_expired_domains(db: Session) -> List[Domain]:
        """检查已过期的域名"""
        now = datetime.utcnow()
        
        domains = db.query(Domain).filter(
            Domain.cert_valid_to <= now,
        ).all()
        
        return domains
    
    @staticmethod
    def delete_domain(db: Session, domain_id: str) -> bool:
        """删除域名"""
        domain = db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            return False
        
        domain_name = domain.domain
        db.delete(domain)
        db.commit()
        logger.info(f"✅ 域名已删除: {domain_name}")
        return True
    
    @staticmethod
    def get_domain_config(db: Session, domain_id: str) -> Optional[dict]:
        """获取域名配置"""
        domain = db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            return None
        
        # 计算剩余天数
        days_remaining = None
        if domain.cert_valid_to:
            days_remaining = (domain.cert_valid_to - datetime.utcnow()).days
        
        return {
            "id": domain.id,
            "domain": domain.domain,
            "email": domain.email,
            "provider": domain.provider,
            "auto_renew": domain.auto_renew,
            "renew_before_days": domain.renew_before_days,
            "cert_valid_from": domain.cert_valid_from.isoformat() if domain.cert_valid_from else None,
            "cert_valid_to": domain.cert_valid_to.isoformat() if domain.cert_valid_to else None,
            "days_remaining": days_remaining,
            "last_renew_at": domain.last_renew_at.isoformat() if domain.last_renew_at else None,
            "created_at": domain.created_at.isoformat(),
        }
