/**
 * stores/auth.js - 认证状态管理
 * 管理用户登录状态、令牌和用户信息，提供登录/注册/登出等操作
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, register as registerApi } from '../api/auth'
import { getProfile } from '../api/user'

export const useAuthStore = defineStore('auth', () => {
  // 从 localStorage 恢复令牌状态
  const token = ref(localStorage.getItem('access_token') || '')
  const isAuthenticated = ref(!!token.value)
  const user = ref(null)

  /**
   * 用户登录
   * 调用登录接口，存储令牌到本地，并获取用户资料
   */
  async function login(username, password) {
    const res = await loginApi(username, password)
    token.value = res.data.access_token
    isAuthenticated.value = true
    // 持久化令牌到 localStorage
    localStorage.setItem('access_token', res.data.access_token)
    localStorage.setItem('refresh_token', res.data.refresh_token)
    await fetchUser()
  }

  /**
   * 用户注册
   * 调用注册接口，注册成功后自动登录
   */
  async function register(username, password) {
    const res = await registerApi(username, password)
    token.value = res.data.access_token
    isAuthenticated.value = true
    localStorage.setItem('access_token', res.data.access_token)
    localStorage.setItem('refresh_token', res.data.refresh_token)
    await fetchUser()
  }

  /** 获取当前登录用户的资料，失败时自动登出 */
  async function fetchUser() {
    try {
      const res = await getProfile()
      user.value = res.data
    } catch {
      logout()
    }
  }

  /** 登出：清除所有认证状态和本地令牌 */
  function logout() {
    token.value = ''
    isAuthenticated.value = false
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return { token, isAuthenticated, user, login, register, fetchUser, logout }
})
