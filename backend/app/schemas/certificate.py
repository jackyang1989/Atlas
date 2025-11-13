"""
证书管理 Schema
文件：backend/app/schemas/certificate.py
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


# ==================== acme.sh ====================

class AcmeStatusResponse(BaseModel):
    """acme.sh 状态响应"""
    installed: bool
    version: Optional[str]
    acme_path: Optional[str]


# ==================== DNS 提供商 ====================

class ProviderInfo(BaseModel):
    """DNS 提供商信息"""
    id: str
    name: str
    dns_type: Optional[str]
    required_keys: List[str]
    key_names: Dict[str, str]


class CertProviderListResponse(BaseModel):
    """DNS 提供商列表响应"""
    total: int
    providers: List[ProviderInfo]


# ==================== 证书操作 ====================

class CertIssueRequest(BaseModel):
    """签发证书请求"""
    domain: str = Field(..., description="域名")
    provider: str = Field("standalone", description="提供商: standalone/cloudflare/aliyun/dnspod")
    api_credentials: Optional[Dict[str, str]] = Field(None, description="DNS API 凭证")
    
    class Config:
        json_schema_extra = {
            "example": {
                "domain": "example.com",
                "provider": "cloudflare",
                "api_credentials": {
                    "CF_Key": "your-api-key",
                    "CF_Email": "your-email@example.com"
                }
            }
        }


class CertRenewRequest(BaseModel):
    """续期证书请求"""
    domain: str = Field(..., description="域名")
    api_credentials: Optional[Dict[str, str]] = Field(None, description="DNS API 凭证（如需要）")


class CertInfoResponse(BaseModel):
    """证书信息响应"""
    domain: str
    cert_path: str
    exists: bool
    valid_from: Optional[str]
    valid_to: Optional[str]
    subject: Optional[str]


# ==================== 过期检查 ====================

class ExpiringDomain(BaseModel):
    """即将过期的域名"""
    domain: str
    cert_valid_to: Optional[str]
    days_remaining: Optional[int]


class ExpiringCertsResponse(BaseModel):
    """即将过期的证书列表"""
    total: int
    domains: List[ExpiringDomain]
