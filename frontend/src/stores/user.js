/**
 * stores/user.js - 用户信息状态管理
 * 管理当前用户的个人资料（ID、用户名、显示名、头像）
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getProfile, updateProfile, updateUsername, uploadAvatar } from '../api/user'

// API 基础地址，用于拼接相对路径的头像 URL
const apiBaseURL = import.meta.env.VITE_API_BASE_URL || ''

/** 将相对路径的头像 URL 转为完整地址 */
function resolveAvatarUrl(url) {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `${apiBaseURL}${url}`
}

export const useUserStore = defineStore('user', () => {
  // 用户基本信息
  const id = ref(null)
  const username = ref('')
  const displayName = ref('')
  const avatarUrl = ref('')

  /** 获取用户资料并更新本地状态 */
  async function fetchProfile() {
    const res = await getProfile()
    const data = res.data
    id.value = data.id
    username.value = data.username
    // 显示名优先使用 display_name，无则使用 username
    displayName.value = data.display_name || data.username
    avatarUrl.value = resolveAvatarUrl(data.avatar_url)
  }

  /** 更新用户显示名 */
  async function updateDisplayName(name) {
    await updateProfile({ display_name: name })
    displayName.value = name
  }

  /** 修改用户名 */
  async function changeUsername(newUsername) {
    await updateUsername(newUsername)
    username.value = newUsername
  }

  /** 上传新头像并更新本地头像 URL */
  async function changeAvatar(file) {
    const res = await uploadAvatar(file)
    avatarUrl.value = resolveAvatarUrl(res.data.avatar_url)
  }

  return { id, username, displayName, avatarUrl, fetchProfile, updateDisplayName, changeUsername, changeAvatar }
})
