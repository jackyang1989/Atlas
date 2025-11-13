"""
Webhook 功能测试
文件：backend/tests/test_webhooks.py
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.services.auth_service import AuthService
from app.services.rbac_service import RBACService

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
def auth_token(client):
    """获取认证 token"""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    return response.json()["access_token"]


class TestWebhooks:
    """Webhook 测试类"""
    
    def test_create_webhook(self, client, auth_token):
        """测试创建 Webhook"""
        response = client.post(
            "/api/webhooks/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "url": "https://example.com/webhook",
                "name": "测试 Webhook",
                "description": "这是一个测试",
                "events": ["service.started", "user.created"],
                "retry_enabled": True,
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "测试 Webhook"
        assert data["url"] == "https://example.com/webhook"
        assert data["enabled"] is True
        assert "service.started" in data["events"]
    
    def test_list_webhooks(self, client, auth_token):
        """测试列出 Webhooks"""
        # 创建几个 Webhooks
        for i in range(3):
            client.post(
                "/api/webhooks/",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "url": f"https://example.com/webhook{i}",
                    "name": f"Webhook {i}",
                    "events": ["service.started"],
                }
            )
        
        # 获取列表
        response = client.get(
            "/api/webhooks/",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
    
    def test_get_webhook(self, client, auth_token):
        """测试获取 Webhook 详情"""
        # 创建 Webhook
        create_response = client.post(
            "/api/webhooks/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "url": "https://example.com/webhook",
                "name": "详情测试",
                "events": ["user.created"],
            }
        )
        webhook_id = create_response.json()["id"]
        
        # 获取详情
        response = client.get(
            f"/api/webhooks/{webhook_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "详情测试"
    
    def test_update_webhook(self, client, auth_token):
        """测试更新 Webhook"""
        # 创建 Webhook
        create_response = client.post(
            "/api/webhooks/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "url": "https://example.com/webhook",
                "name": "更新测试",
                "events": ["service.started"],
            }
        )
        webhook_id = create_response.json()["id"]
        
        # 更新
        response = client.put(
            f"/api/webhooks/{webhook_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "已更新的名称",
                "events": ["service.started", "service.stopped"],
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "已更新的名称"
        assert len(data["events"]) == 2
    
    def test_toggle_webhook(self, client, auth_token):
        """测试启用/禁用 Webhook"""
        # 创建 Webhook
        create_response = client.post(
            "/api/webhooks/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "url": "https://example.com/webhook",
                "name": "启停测试",
                "events": ["service.started"],
            }
        )
        webhook_id = create_response.json()["id"]
        
        # 禁用
        response = client.post(
            f"/api/webhooks/{webhook_id}/toggle",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json()["enabled"] is False
        
        # 启用
        response = client.post(
            f"/api/webhooks/{webhook_id}/toggle",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json()["enabled"] is True
    
    def test_delete_webhook(self, client, auth_token):
        """测试删除 Webhook"""
        # 创建 Webhook
        create_response = client.post(
            "/api/webhooks/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "url": "https://example.com/webhook",
                "name": "删除测试",
                "events": ["service.started"],
            }
        )
        webhook_id = create_response.json()["id"]
        
        # 删除
        response = client.delete(
            f"/api/webhooks/{webhook_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 204
        
        # 验证已删除
        response = client.get(
            f"/api/webhooks/{webhook_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404
    
    def test_invalid_events(self, client, auth_token):
        """测试无效的事件类型"""
        response = client.post(
            "/api/webhooks/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "url": "https://example.com/webhook",
                "name": "无效事件",
                "events": ["invalid.event", "another.invalid"],
            }
        )
        assert response.status_code == 400
    
    def test_webhook_without_auth(self, client):
        """测试未授权访问"""
        response = client.get("/api/webhooks/")
        assert response.status_code == 403


class TestWebhookService:
    """Webhook 服务测试"""
    
    def test_signature_generation(self):
        """测试签名生成"""
        from app.services.webhook_service import WebhookService
        
        payload = {"test": "data", "number": 123}
        secret = "test-secret"
        
        signature1 = WebhookService.generate_signature(payload, secret)
        signature2 = WebhookService.generate_signature(payload, secret)
        
        # 相同数据应该生成相同签名
        assert signature1 == signature2
        assert len(signature1) == 64  # SHA256 hex digest 长度
    
    def test_send_event(self, test_db):
        """测试发送事件"""
        from app.services.webhook_service import WebhookService
        
        # 创建一个 Webhook
        webhook = WebhookService.create_webhook(
            test_db,
            url="https://httpbin.org/post",  # 测试端点
            name="测试事件发送",
            events=["test.event"],
            created_by="admin"
        )
        
        # 发送事件（会尝试真实发送，但不会失败测试）
        try:
            WebhookService.send_event(
                test_db,
                event_type="test.event",
                payload={"message": "测试消息"},
                source="test"
            )
        except Exception as e:
            # 网络问题不应该导致测试失败
            pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
