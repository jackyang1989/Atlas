"""
代理规则系统 - 数据模型
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base
import json


class ProxyRule(Base):
    """代理规则配置"""
    __tablename__ = "proxy_rules"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(255))
    
    # 规则类型: domain/ip/geo/port/protocol
    rule_type = Column(String(50), nullable=False, index=True)
    
    # 匹配模式
    match_pattern = Column(Text, nullable=False)
    # 域名: *.example.com, example.com
    # IP: 192.168.1.0/24, 10.0.0.1
    # 地域: CN, US, HK
    # 端口: 80, 443, 8080-8090
    
    # 动作: proxy/direct/reject
    action = Column(String(20), nullable=False, default="proxy")
    
    # 优先级（数值越大优先级越高）
    priority = Column(Integer, default=0, index=True)
    
    # 是否启用
    enabled = Column(Boolean, default=True, index=True)
    
    # 应用范围（可选：指定服务或用户）
    service_ids = Column(Text)  # JSON: ["svc1", "svc2"]
    user_ids = Column(Text)     # JSON: ["user1", "user2"]
    
    # 统计
    hit_count = Column(Integer, default=0)
    last_hit_at = Column(DateTime)
    
    # 元数据
    tags = Column(Text)  # JSON: ["internal", "cdn"]
    notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rule_type": self.rule_type,
            "match_pattern": self.match_pattern,
            "action": self.action,
            "priority": self.priority,
            "enabled": self.enabled,
            "service_ids": json.loads(self.service_ids) if self.service_ids else [],
            "user_ids": json.loads(self.user_ids) if self.user_ids else [],
            "hit_count": self.hit_count,
            "last_hit_at": self.last_hit_at.isoformat() if self.last_hit_at else None,
            "tags": json.loads(self.tags) if self.tags else [],
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GlobalProxyConfig(Base):
    """全局代理配置"""
    __tablename__ = "global_proxy_config"
    
    id = Column(String(36), primary_key=True)
    
    # 全局代理开关
    enabled = Column(Boolean, default=True)
    
    # 默认动作: proxy/direct
    default_action = Column(String(20), default="proxy")
    
    # 规则匹配模式: priority/first_match
    rule_match_mode = Column(String(20), default="priority")
    
    # GeoIP 数据库路径
    geoip_db_path = Column(String(255))
    
    # 统计
    total_requests = Column(Integer, default=0)
    proxied_requests = Column(Integer, default=0)
    direct_requests = Column(Integer, default=0)
    rejected_requests = Column(Integer, default=0)
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "enabled": self.enabled,
            "default_action": self.default_action,
            "rule_match_mode": self.rule_match_mode,
            "geoip_db_path": self.geoip_db_path,
            "stats": {
                "total_requests": self.total_requests,
                "proxied_requests": self.proxied_requests,
                "direct_requests": self.direct_requests,
                "rejected_requests": self.rejected_requests,
            },
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# 预定义规则类型
RULE_TYPES = {
    "domain": {
        "name": "域名规则",
        "description": "基于域名匹配",
        "examples": ["*.google.com", "example.com", "*.cn"],
    },
    "ip": {
        "name": "IP 规则",
        "description": "基于 IP 地址或 CIDR 匹配",
        "examples": ["192.168.1.0/24", "10.0.0.1", "172.16.0.0/12"],
    },
    "geo": {
        "name": "地域规则",
        "description": "基于地理位置匹配",
        "examples": ["CN", "US", "HK", "JP"],
    },
    "port": {
        "name": "端口规则",
        "description": "基于端口号匹配",
        "examples": ["80", "443", "8080-8090"],
    },
    "protocol": {
        "name": "协议规则",
        "description": "基于协议类型匹配",
        "examples": ["http", "https", "tcp", "udp"],
    },
}


# 预定义动作
RULE_ACTIONS = {
    "proxy": {
        "name": "使用代理",
        "description": "流量通过代理服务器",
        "icon": "🔀",
    },
    "direct": {
        "name": "直接连接",
        "description": "流量直接访问，不经过代理",
        "icon": "🔗",
    },
    "reject": {
        "name": "拒绝连接",
        "description": "阻止此流量",
        "icon": "🚫",
    },
}
