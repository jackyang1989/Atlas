# Webhook 系统部署指南

## 📋 部署步骤

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 创建数据库表

```bash
# 方式 1：使用迁移脚本
python scripts/create_webhook_tables.py

# 方式 2：启动应用时自动创建
python -m uvicorn app.main:app --reload --port 5000
```

### 3. 验证安装

访问 API 文档检查 Webhook 端点：

```
http://localhost:5000/docs
```

查找 **"Webhooks"** 标签，应该看到以下端点：

- `GET /api/webhooks/` - 列出所有
- `POST /api/webhooks/` - 创建
- `GET /api/webhooks/{id}` - 详情
- `PUT /api/webhooks/{id}` - 更新
- `DELETE /api/webhooks/{id}` - 删除
- `POST /api/webhooks/{id}/toggle` - 启用/禁用
- `POST /api/webhooks/{id}/test` - 测试
- `GET /api/webhooks/{id}/logs` - 日志
- `GET /api/webhooks/{id}/stats` - 统计

### 4. 运行测试

```bash
# 运行 Webhook 测试
pytest tests/test_webhooks.py -v

# 运行所有测试
pytest tests/ -v
```

---

## 🧪 快速测试

### 使用 curl 测试

```bash
# 1. 登录获取 token
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.access_token')

# 2. 创建 Webhook
curl -X POST http://localhost:5000/api/webhooks/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://webhook.site/YOUR-UNIQUE-URL",
    "name": "测试 Webhook",
    "description": "这是测试",
    "events": ["service.started", "user.created"]
  }'

# 3. 列出 Webhooks
curl -X GET http://localhost:5000/api/webhooks/ \
  -H "Authorization: Bearer $TOKEN"

# 4. 测试 Webhook（替换 WEBHOOK_ID）
curl -X POST http://localhost:5000/api/webhooks/WEBHOOK_ID/test \
  -H "Authorization: Bearer $TOKEN"
```

### 使用 Python 测试

```python
import requests

# 登录
response = requests.post(
    "http://localhost:5000/api/auth/login",
    json={"username": "admin", "password": "admin123"}
)
token = response.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# 创建 Webhook
webhook_data = {
    "url": "https://webhook.site/YOUR-UNIQUE-URL",
    "name": "Python 测试 Webhook",
    "events": ["service.started", "user.created"],
    "retry_enabled": True,
}

response = requests.post(
    "http://localhost:5000/api/webhooks/",
    json=webhook_data,
    headers=headers
)

print("创建结果:", response.json())

# 列出所有 Webhooks
response = requests.get(
    "http://localhost:5000/api/webhooks/",
    headers=headers
)

print("Webhook 列表:", response.json())
```

---

## 🔧 使用 Webhook.site 测试

1. 访问 https://webhook.site/
2. 复制你的唯一 URL（例如：`https://webhook.site/abcd1234`）
3. 在 ATLAS 中创建 Webhook，URL 使用上面的地址
4. 触发事件（创建服务、用户等）
5. 在 Webhook.site 查看收到的请求

---

## 🎯 支持的事件类型

### 服务事件
- `service.started` - 服务已启动
- `service.stopped` - 服务已停止
- `service.created` - 服务已创建
- `service.deleted` - 服务已删除

### 用户事件
- `user.created` - 用户已创建
- `user.deleted` - 用户已删除
- `user.disabled` - 用户已禁用
- `user.enabled` - 用户已启用
- `user.quota_exceeded` - 用户流量超限
- `user.expired` - 用户已过期

### 域名事件
- `domain.created` - 域名已添加
- `domain.cert_issued` - 证书已签发
- `domain.cert_renewed` - 证书已续期
- `domain.cert_expiring` - 证书即将过期
- `domain.deleted` - 域名已删除

### 备份事件
- `backup.created` - 备份已创建
- `backup.restored` - 备份已恢复
- `backup.deleted` - 备份已删除

### 系统事件
- `system.health_warning` - 系统健康告警
- `system.resource_alert` - 系统资源告警
- `system.error` - 系统错误

---

## 🔐 签名验证

Webhook 请求包含 HMAC-SHA256 签名用于验证：

### 请求头
```
X-ATLAS-Event: service.started
X-ATLAS-Signature: <HMAC-SHA256 签名>
Content-Type: application/json
```

### 验证示例（Python）

```python
import hmac
import hashlib
import json

def verify_webhook_signature(payload, signature, secret):
    """验证 Webhook 签名"""
    message = json.dumps(payload, sort_keys=True).encode('utf-8')
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        message,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

# 使用示例
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    signature = request.headers.get('X-ATLAS-Signature')
    secret = 'your-webhook-secret'
    
    if not verify_webhook_signature(request.json, signature, secret):
        return 'Invalid signature', 403
    
    # 处理事件
    event_type = request.headers.get('X-ATLAS-Event')
    payload = request.json
    
    return 'OK', 200
```

---

## 📊 监控和日志

### 查看 Webhook 调用日志

```bash
# 获取特定 Webhook 的日志
curl -X GET "http://localhost:5000/api/webhooks/WEBHOOK_ID/logs?limit=50" \
  -H "Authorization: Bearer $TOKEN"

# 获取最近 24 小时的所有日志
curl -X GET "http://localhost:5000/api/webhooks/logs/recent?hours=24" \
  -H "Authorization: Bearer $TOKEN"
```

### 查看统计信息

```bash
curl -X GET "http://localhost:5000/api/webhooks/WEBHOOK_ID/stats" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔧 故障排查

### Webhook 未触发

1. **检查 Webhook 是否启用**
   ```bash
   curl -X GET http://localhost:5000/api/webhooks/WEBHOOK_ID \
     -H "Authorization: Bearer $TOKEN" | jq '.enabled'
   ```

2. **检查事件订阅**
   ```bash
   curl -X GET http://localhost:5000/api/webhooks/WEBHOOK_ID \
     -H "Authorization: Bearer $TOKEN" | jq '.events'
   ```

3. **查看错误日志**
   ```bash
   curl -X GET http://localhost:5000/api/webhooks/WEBHOOK_ID/logs \
     -H "Authorization: Bearer $TOKEN" | jq '.items[] | select(.success==false)'
   ```

### Webhook 调用失败

1. **检查 URL 是否可达**
   ```bash
   curl -I https://your-webhook-url.com
   ```

2. **查看最后一次错误**
   ```bash
   curl -X GET http://localhost:5000/api/webhooks/WEBHOOK_ID \
     -H "Authorization: Bearer $TOKEN" | jq '.last_error'
   ```

3. **测试 Webhook**
   ```bash
   curl -X POST http://localhost:5000/api/webhooks/WEBHOOK_ID/test \
     -H "Authorization: Bearer $TOKEN"
   ```

---

## ✅ 验证清单

- [ ] 依赖已安装（`pip install -r requirements.txt`）
- [ ] 数据库表已创建（`webhooks`, `webhook_logs`）
- [ ] API 文档可访问（`/docs`）
- [ ] 测试通过（`pytest tests/test_webhooks.py`）
- [ ] 可以创建 Webhook
- [ ] 可以测试 Webhook
- [ ] 可以查看日志
- [ ] 签名验证正常

---

## 📚 相关文档

- Webhook 模型：`backend/app/models/webhook.py`
- Webhook 服务：`backend/app/services/webhook_service.py`
- Webhook API：`backend/app/api/webhooks.py`
- Webhook Schema：`backend/app/schemas/webhook.py`
- Webhook 测试：`backend/tests/test_webhooks.py`
