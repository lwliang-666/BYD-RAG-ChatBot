/**
 * request.js - Axios 请求封装
 * 创建统一的 axios 实例，配置请求/响应拦截器
 * - 请求拦截：自动附加 Authorization 令牌
 * - 响应拦截：401 时自动尝试刷新令牌并重试请求
 */
import axios from 'axios'

// 创建 axios 实例，设置基础超时时间
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000,
})

// 请求拦截器：在每个请求头中自动附加访问令牌
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：处理 401 未授权错误，自动刷新令牌并重试
api.interceptors.response.use(
  // 正常响应直接返回
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    // 登录/注册接口的 401 直接抛出，不走 token 刷新逻辑
    const isAuthEndpoint = originalRequest.url?.includes('/api/auth/login') || originalRequest.url?.includes('/api/auth/register')

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      // 标记已重试，防止无限循环
      originalRequest._retry = true
      const refreshToken = localStorage.getItem('refresh_token')

      if (refreshToken) {
        try {
          // 使用 refresh_token 获取新的 access_token
          const res = await axios.post('/api/auth/refresh', { refresh_token: refreshToken })
          // 更新本地存储的令牌
          localStorage.setItem('access_token', res.data.access_token)
          localStorage.setItem('refresh_token', res.data.refresh_token)
          // 用新令牌重试原始请求
          originalRequest.headers.Authorization = `Bearer ${res.data.access_token}`
          return api(originalRequest)
        } catch {
          // 刷新令牌失败，清除本地令牌并跳转登录页
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      } else {
        // 无 refresh_token，清除本地令牌并跳转登录页
        localStorage.removeItem('access_token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
