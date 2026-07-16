/**
 * auth.js - 认证相关 API 接口
 * 封装用户登录、注册、令牌刷新等认证相关的 HTTP 请求
 */
import api from './request'

/** 用户登录，返回 access_token 和 refresh_token */
export function login(username, password) {
  return api.post('/api/auth/login', { username, password })
}

/** 用户注册，注册成功后自动返回令牌 */
export function register(username, password) {
  return api.post('/api/auth/register', { username, password })
}

/** 使用 refresh_token 刷新 access_token，实现无感续期 */
export function refreshToken(refresh_token) {
  return api.post('/api/auth/refresh', { refresh_token })
}
