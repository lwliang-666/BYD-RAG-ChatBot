import api from './request'

export function login(username, password) {
  return api.post('/api/auth/login', { username, password })
}

export function register(username, password) {
  return api.post('/api/auth/register', { username, password })
}

export function refreshToken(refresh_token) {
  return api.post('/api/auth/refresh', { refresh_token })
}
