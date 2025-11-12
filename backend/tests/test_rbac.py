"""
RBAC 权限系统测试
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.services.auth_service import AuthService
from app.services.rbac_service import RBACService
from app.models.admin import AdminUser
from app.models.rbac import AdminRole, AdminPermission

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db():
    """创建测试数据库"""
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    # 初始化 RBAC
    RBACService.init_permissions(db)
    RBACService.init_roles(db)
    
    # 创建默认管理员
    AuthService.create_default_admin(db)
    
    def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    yield db
    db.close()


@pytest.fixture
def client(test_db):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """获取管理员 token"""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    return response.json()["access_token"]


class TestPermissions:
    """权限测试"""
    
    def test_init_permissions(self, test_db):
        """测试权限初始化"""
        permissions = test_db.query(AdminPermission).all()
        assert len(permissions) > 0
        
        # 验证关键权限存在
        perm_names = [p.name for p in permissions]
        assert "read:service" in perm_names
        assert "write:user" in perm_names
        assert "delete:admin" in perm_names
    
    def test_list_permissions_api(self, client, admin_token):
        """测试获取权限列表 API"""
        response = client.get(
            "/api/rbac/permissions",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] > 0
    
    def test_get_permissions_by_resource(self, client, admin_token):
        """测试按资源获取权限"""
        response = client.get(
            "/api/rbac/permissions/by-resource/service",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resource"] == "service"
        assert len(data["permissions"]) > 0


class TestRoles:
    """角色测试"""
    
    def test_init_roles(self, test_db):
        """测试角色初始化"""
        roles = test_db.query(AdminRole).all()
        assert len(roles) >= 3  # admin, operator, viewer
        
        role_names = [r.name for r in roles]
        assert "admin" in role_names
        assert "operator" in role_names
        assert "viewer" in role_names
    
    def test_admin_has_all_permissions(self, test_db):
        """测试 admin 角色有所有权限"""
        admin_role = RBACService.get_role_by_name(test_db, "admin")
        assert admin_role is not None
        assert len(admin_role.permissions) > 0
    
    def test_viewer_has_limited_permissions(self, test_db):
        """测试 viewer 角色权限受限"""
        viewer_role = RBACService.get_role_by_name(test_db, "viewer")
        assert viewer_role is not None
        
        # viewer 应该只有 read 权限
        perm_names = [p.name for p in viewer_role.permissions]
        assert all("read:" in perm for perm in perm_names)
        
        # 不应该有 delete 权限
        assert not any("delete:" in perm for perm in perm_names)
    
    def test_list_roles_api(self, client, admin_token):
        """测试获取角色列表 API"""
        response = client.get(
            "/api/rbac/roles",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
    
    def test_create_role_api(self, client, admin_token, test_db):
        """测试创建角色 API"""
        # 获取 viewer 角色的权限
        viewer_role = RBACService.get_role_by_name(test_db, "viewer")
        perm_ids = [p.id for p in viewer_role.permissions]
        
        response = client.post(
            "/api/rbac/roles",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "custom_role",
                "description": "自定义角色",
                "permission_ids": perm_ids
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "custom_role"
    
    def test_delete_builtin_role_fails(self, client, admin_token):
        """测试删除内置角色失败"""
        # 先获取 admin 角色的 ID
        response = client.get(
            "/api/rbac/roles",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        admin_role = None
        for role in response.json()["items"]:
            if role["name"] == "admin":
                admin_role = role
                break
        
        assert admin_role is not None
        
        # 尝试删除
        response = client.delete(
            f"/api/rbac/roles/{admin_role['id']}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400


class TestAdminUsers:
    """管理员用户测试"""
    
    def test_create_admin_user_api(self, client, admin_token, test_db):
        """测试创建管理员用户 API"""
        operator_role = RBACService.get_role_by_name(test_db, "operator")
        
        response = client.post(
            "/api/rbac/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "operator_user",
                "password": "operator123456",
                "role_id": operator_role.id
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "operator_user"
    
    def test_assign_role_api(self, client, admin_token, test_db):
        """测试分配角色 API"""
        # 创建用户
        viewer_role = RBACService.get_role_by_name(test_db, "viewer")
        operator_role = RBACService.get_role_by_name(test_db, "operator")
        
        create_response = client.post(
            "/api/rbac/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "test_user_role",
                "password": "test123456",
                "role_id": viewer_role.id
            }
        )
        user_id = create_response.json()["id"]
        
        # 分配新角色
        assign_response = client.put(
            f"/api/rbac/users/{user_id}/role",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role_id": operator_role.id}
        )
        assert assign_response.status_code == 200
        assert assign_response.json()["role_id"] == operator_role.id
    
    def test_disable_user_api(self, client, admin_token, test_db):
        """测试禁用用户 API"""
        viewer_role = RBACService.get_role_by_name(test_db, "viewer")
        
        create_response = client.post(
            "/api/rbac/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "user_to_disable",
                "password": "test123456",
                "role_id": viewer_role.id
            }
        )
        user_id = create_response.json()["id"]
        
        # 禁用用户
        disable_response = client.post(
            f"/api/rbac/users/{user_id}/disable",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert disable_response.status_code == 200
        assert disable_response.json()["is_active"] is False
    
    def test_cannot_disable_last_admin(self, client, admin_token, test_db):
        """测试不能禁用最后一个管理员"""
        # 获取 admin 用户
        admin_user = test_db.query(AdminUser).filter(
            AdminUser.username == "admin"
        ).first()
        
        # 尝试禁用（应该失败，因为这是唯一的 admin）
        response = client.post(
            f"/api/rbac/users/{admin_user.id}/disable",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400


class TestPermissionChecks:
    """权限检查测试"""
    
    def test_admin_has_permission(self, test_db):
        """测试 admin 用户有权限"""
        admin_user = test_db.query(AdminUser).filter(
            AdminUser.username == "admin"
        ).first()
        
        assert RBACService.has_permission(admin_user, "read:service")
        assert RBACService.has_permission(admin_user, "write:user")
        assert RBACService.has_permission(admin_user, "delete:admin")
    
    def test_viewer_lacks_write_permission(self, test_db):
        """测试 viewer 用户缺少写权限"""
        import uuid
        from app.utils.security import hash_password
        
        viewer_role = RBACService.get_role_by_name(test_db, "viewer")
        
        viewer_user = AdminUser(
            id=str(uuid.uuid4()),
            username="viewer_user",
            password_hash=hash_password("viewer123456"),
            role_id=viewer_role.id,
            is_active=True,
        )
        test_db.add(viewer_user)
        test_db.commit()
        
        # viewer 应该能读
        assert RBACService.has_permission(viewer_user, "read:service")
        
        # viewer 不应该能写
        assert not RBACService.has_permission(viewer_user, "write:service")
    
    def test_disabled_user_has_no_permission(self, test_db):
        """测试禁用用户无权限"""
        import uuid
        from app.utils.security import hash_password
        
        admin_role = RBACService.get_role_by_name(test_db, "admin")
        
        disabled_user = AdminUser(
            id=str(uuid.uuid4()),
            username="disabled_user",
            password_hash=hash_password("disabled123456"),
            role_id=admin_role.id,
            is_active=False,  # 禁用
        )
        test_db.add(disabled_user)
        test_db.commit()
        
        # 禁用用户没有权限
        assert not RBACService.has_permission(disabled_user, "read:service")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
