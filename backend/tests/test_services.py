import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.services.auth_service import AuthService

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    AuthService.create_default_admin(db)
    
    def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    yield db
    db.close()

@pytest.fixture
def client(test_db):
    return TestClient(app)

@pytest.fixture
def auth_token(client):
    """获取认证 token"""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    return response.json()["access_token"]

def test_create_service(client, auth_token):
    """测试创建服务"""
    response = client.post(
        "/api/services/",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "VLESS_Test",
            "protocol": "vless",
            "port": 9001,
            "cert_domain": "example.com"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "VLESS_Test"
    assert data["port"] == 9001
    assert data["status"] == "stopped"

def test_list_services(client, auth_token):
    """测试列表服务"""
    # 创建服务
    client.post(
        "/api/services/",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "Service1",
            "protocol": "vless",
            "port": 9001,
            "cert_domain": "example.com"
        }
    )
    
    # 获取列表
    response = client.get(
        "/api/services/",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1

def test_toggle_service(client, auth_token):
    """测试启停服务"""
    # 创建服务
    create_response = client.post(
        "/api/services/",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "Toggle_Test",
            "protocol": "vless",
            "port": 9002,
            "cert_domain": "example.com"
        }
    )
    service_id = create_response.json()["id"]
    
    # 启动服务
    response = client.put(
        f"/api/services/{service_id}/toggle",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.json()["status"] == "running"

def test_delete_service(client, auth_token):
    """测试删除服务"""
    # 创建服务
    create_response = client.post(
        "/api/services/",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "Delete_Test",
            "protocol": "vless",
            "port": 9003,
            "cert_domain": "example.com"
        }
    )
    service_id = create_response.json()["id"]
    
    # 删除服务
    response = client.delete(
        f"/api/services/{service_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 204
