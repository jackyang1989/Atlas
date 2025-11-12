import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 自动添加 token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器 - 处理错误
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 401 未授权，清除 token 并重定向到登录
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ==================== Auth 相关接口 ====================
export const authAPI = {
  login: (username, password) =>
    apiClient.post('/api/auth/login', { username, password }),
  
  getCurrentUser: () =>
    apiClient.get('/api/auth/me'),
  
  changePassword: (oldPassword, newPassword) =>
    apiClient.post('/api/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    }),
};

// ==================== Monitor/System 相关接口 ====================
export const monitorAPI = {
  // 健康检查（无需认证）
  healthCheck: () =>
    apiClient.get('/api/monitor/health'),
  
  // 仪表盘数据（完整系统状态）
  dashboard: () =>
    apiClient.get('/api/monitor/dashboard'),
  
  // 系统统计
  stats: () =>
    apiClient.get('/api/monitor/system'),
  
  // CPU 统计
  cpu: () =>
    apiClient.get('/api/monitor/cpu'),
  
  // 内存统计
  memory: () =>
    apiClient.get('/api/monitor/memory'),
  
  // 磁盘统计
  disk: () =>
    apiClient.get('/api/monitor/disk'),
  
  // 网络统计
  network: () =>
    apiClient.get('/api/monitor/network'),
};

// ==================== Services (VPN 服务) 相关接口 ====================
export const servicesAPI = {
  list: (skip = 0, limit = 10) =>
    apiClient.get('/api/services/', { params: { skip, limit } }),
  
  create: (data) =>
    apiClient.post('/api/services/', data),
  
  get: (serviceId) =>
    apiClient.get(`/api/services/${serviceId}`),
  
  update: (serviceId, data) =>
    apiClient.put(`/api/services/${serviceId}`, data),
  
  toggle: (serviceId) =>
    apiClient.put(`/api/services/${serviceId}/toggle`),
  
  delete: (serviceId) =>
    apiClient.delete(`/api/services/${serviceId}`),
};

// ==================== Users (用户) 相关接口 ====================
export const usersAPI = {
  list: (skip = 0, limit = 10, status = null) =>
    apiClient.get('/api/users/', { params: { skip, limit, status_filter: status } }),
  
  create: (data) =>
    apiClient.post('/api/users/', data),
  
  get: (userId) =>
    apiClient.get(`/api/users/${userId}`),
  
  update: (userId, data) =>
    apiClient.put(`/api/users/${userId}`, data),
  
  addTraffic: (userId, amount) =>
    apiClient.post(`/api/users/${userId}/traffic`, { traffic_gb: amount }),
  
  resetTraffic: (userId) =>
    apiClient.post(`/api/users/${userId}/traffic/reset`),
  
  setServices: (userId, serviceIds) =>
    apiClient.put(`/api/users/${userId}/services`, { service_ids: serviceIds }),
  
  enable: (userId) =>
    apiClient.post(`/api/users/${userId}/enable`),
  
  disable: (userId) =>
    apiClient.post(`/api/users/${userId}/disable`),
  
  getConfig: (userId) =>
    apiClient.get(`/api/users/${userId}/config`),
  
  delete: (userId) =>
    apiClient.delete(`/api/users/${userId}`),
};

// ==================== Domains (域名) 相关接口 ====================
export const domainsAPI = {
  list: (skip = 0, limit = 10) =>
    apiClient.get('/api/domains/', { params: { skip, limit } }),
  
  create: (data) =>
    apiClient.post('/api/domains/', data),
  
  get: (domainId) =>
    apiClient.get(`/api/domains/${domainId}`),
  
  update: (domainId, data) =>
    apiClient.put(`/api/domains/${domainId}`, data),
  
  delete: (domainId) =>
    apiClient.delete(`/api/domains/${domainId}`),
  
  // ✅ 修复：移除重复的 status() 方法
  // 使用统一的 stats() 方法获取统计信息
  stats: () =>
    apiClient.get('/api/domains/status/all'),
};

// ==================== Components (组件) 相关接口 ====================
export const componentsAPI = {
  list: (skip = 0, limit = 10, typeFilter = null) =>
    apiClient.get('/api/components/', { params: { skip, limit, type_filter: typeFilter } }),
  
  create: (data) =>
    apiClient.post('/api/components/', data),
  
  get: (componentId) =>
    apiClient.get(`/api/components/${componentId}`),
  
  update: (componentId, data) =>
    apiClient.put(`/api/components/${componentId}`, data),
  
  install: (componentId, force = false) =>
    apiClient.post(`/api/components/${componentId}/install`, { force }),
  
  uninstall: (componentId) =>
    apiClient.post(`/api/components/${componentId}/uninstall`),
  
  checkUpdate: (componentId) =>
    apiClient.get(`/api/components/${componentId}/check-update`),
  
  upgrade: (componentId) =>
    apiClient.post(`/api/components/${componentId}/upgrade`),
  
  delete: (componentId) =>
    apiClient.delete(`/api/components/${componentId}`),
};

// ==================== Backups (备份) 相关接口 ====================
export const backupsAPI = {
  list: () =>
    apiClient.get('/api/backups/'),
  
  create: (includeData = true, includeConfig = true, description = null) =>
    apiClient.post('/api/backups/', {
      include_data: includeData,
      include_config: includeConfig,
      description,
    }),
  
  restore: (filename, force = false) =>
    apiClient.post('/api/backups/restore', { filename, force }),
  
  download: (filename) =>
    apiClient.get(`/api/backups/download/${filename}`, { responseType: 'blob' }),
  
  delete: (filename) =>
    apiClient.delete(`/api/backups/${filename}`),
  
  cleanup: (days = 30) =>
    apiClient.post('/api/backups/cleanup', null, { params: { days } }),
};

// ==================== Alerts (告警) 相关接口 ====================
export const alertsAPI = {
  // 发送测试告警邮件
  test: (email) =>
    apiClient.post('/api/alerts/test', { email }),
  
  // 发送告警
  send: (type, params, recipients) =>
    apiClient.post('/api/alerts/send', { type, params, recipients }),
  
  // 获取告警配置
  getConfig: () =>
    apiClient.get('/api/alerts/config'),
};

export default apiClient;
