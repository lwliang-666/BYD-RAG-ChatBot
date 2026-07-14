import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, register as registerApi } from '../api/auth'
import { getProfile } from '../api/user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const isAuthenticated = ref(!!token.value)
  const user = ref(null)

  async function login(username, password) {
    const res = await loginApi(username, password)
    token.value = res.data.access_token
    isAuthenticated.value = true
    localStorage.setItem('access_token', res.data.access_token)
    localStorage.setItem('refresh_token', res.data.refresh_token)
    await fetchUser()
  }

  async function register(username, password) {
    const res = await registerApi(username, password)
    token.value = res.data.access_token
    isAuthenticated.value = true
    localStorage.setItem('access_token', res.data.access_token)
    localStorage.setItem('refresh_token', res.data.refresh_token)
    await fetchUser()
  }

  async function fetchUser() {
    try {
      const res = await getProfile()
      user.value = res.data
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = ''
    isAuthenticated.value = false
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return { token, isAuthenticated, user, login, register, fetchUser, logout }
})
