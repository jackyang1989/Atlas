"""
RBAC 权限系统模型
"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import json

# 关联表：角色-权限
role_permission_association = Table(
    'role_permission_association',
    Base.metadata,
    Column('role_id', String(36), ForeignKey('admin_roles.id'), primary_key=True),
    Column('permission_id', String(36), ForeignKey('admin_permissions.id'), primary_key=True)
)


class AdminRole(Base):
    """管理员角色"""
    __tablename__ = "admin_roles"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(50), unique=True, nullable=False, index=True)  # admin, operator, viewer
    description = Column(String(255))
    permissions = relationship(
        "AdminPermission",
        secondary=role_permission_association,
        back_populates="roles"
    )
    admin_users = relationship("AdminUser", back_populates="role")
    is_builtin = Column(Boolean, default=False)  # 内置角色
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<AdminRole {self.name}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_builtin": self.is_builtin,
            "permissions": [p.to_dict() for p in self.permissions],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AdminPermission(Base):
    """管理员权限"""
    __tablename__ = "admin_permissions"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255))
    resource = Column(String(50))  # service, user, domain, component, backup, admin
    action = Column(String(50))    # read, write, delete, execute
    roles = relationship(
        "AdminRole",
        secondary=role_permission_association,
        back_populates="permissions"
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<AdminPermission {self.name}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "resource": self.resource,
            "action": self.action,
        }


class AdminUser(Base):
    """管理员用户（修改版本，添加 role_id）"""
    __tablename__ = "admin_users"
    
    id = Column(String(36), primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(String(36), ForeignKey('admin_roles.id'))  # ✨ 新增：角色关联
    role = relationship("AdminRole", back_populates="admin_users")
    
    totp_secret = Column(String(32), nullable=True)
    totp_enabled = Column(Boolean, default=False)
    
    last_login = Column(DateTime, nullable=True)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)  # ✨ 新增：激活状态
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<AdminUser {self.username}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role_id": self.role_id,
            "role": self.role.to_dict() if self.role else None,
            "totp_enabled": self.totp_enabled,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def has_permission(self, permission_name: str) -> bool:
        """检查用户是否有指定权限"""
        if not self.role:
            return False
        return any(p.name == permission_name for p in self.role.permissions)
    
    def has_permissions(self, permission_names: list) -> bool:
        """检查用户是否有所有指定权限"""
        return all(self.has_permission(perm) for perm in permission_names)


# ==================== 预定义的权限列表 ====================

PERMISSIONS = [
    # 服务管理权限
    ("read:service", "查看服务", "service", "read"),
    ("write:service", "创建/修改服务", "service", "write"),
    ("delete:service", "删除服务", "service", "delete"),
    ("execute:service", "启停服务", "service", "execute"),
    
    # 用户管理权限
    ("read:user", "查看用户", "user", "read"),
    ("write:user", "创建/修改用户", "user", "write"),
    ("delete:user", "删除用户", "user", "delete"),
    ("execute:user", "禁用/启用用户", "user", "execute"),
    
    # 域名管理权限
    ("read:domain", "查看域名", "domain", "read"),
    ("write:domain", "创建/修改域名", "domain", "write"),
    ("delete:domain", "删除域名", "domain", "delete"),
    ("execute:domain", "申请/续期证书", "domain", "execute"),
    
    # 组件管理权限
    ("read:component", "查看组件", "component", "read"),
    ("write:component", "注册组件", "component", "write"),
    ("delete:component", "删除组件", "component", "delete"),
    ("execute:component", "安装/升级/卸载组件", "component", "execute"),
    
    # 备份管理权限
    ("read:backup", "查看备份", "backup", "read"),
    ("write:backup", "创建备份", "backup", "write"),
    ("delete:backup", "删除备份", "backup", "delete"),
    ("execute:backup", "恢复备份", "backup", "execute"),
    
    # 管理员管理权限
    ("read:admin", "查看管理员", "admin", "read"),
    ("write:admin", "创建/修改管理员", "admin", "write"),
    ("delete:admin", "删除管理员", "admin", "delete"),
    ("write:role", "修改角色权限", "admin", "write"),
    
    # 系统管理权限
    ("read:system", "查看系统信息", "system", "read"),
    ("execute:system", "执行系统操作", "system", "execute"),
]

# ==================== 预定义的角色配置 ====================

ROLES_CONFIG = {
    "admin": {
        "description": "系统管理员，拥有所有权限",
        "permissions": [perm[0] for perm in PERMISSIONS],  # 所有权限
    },
    "operator": {
        "description": "运维人员，可以管理服务和用户，不能修改安全设置",
        "permissions": [
            "read:service", "write:service", "delete:service", "execute:service",
            "read:user", "write:user", "delete:user", "execute:user",
            "read:domain", "write:domain", "delete:domain", "execute:domain",
            "read:component", "execute:component",
            "read:backup", "write:backup", "execute:backup",
            "read:system", "read:admin",
        ],
    },
    "viewer": {
        "description": "观察者，只能查看信息，无法修改任何内容",
        "permissions": [
            "read:service",
            "read:user",
            "read:domain",
            "read:component",
            "read:backup",
            "read:system",
            "read:admin",
        ],
    },
}
