/**
 * user.js - 用户相关 API 接口
 * 封装用户资料查询、修改用户名、上传头像等 HTTP 请求
 */
import api from './request'

/** 获取当前登录用户的个人资料 */
export function getProfile() {
  return api.get('/api/user/profile')
}

/** 更新用户资料（如显示名称） */
export function updateProfile(data) {
  return api.put('/api/user/profile', data)
}

/** 修改用户名 */
export function updateUsername(username) {
  return api.put('/api/user/username', { username })
}

/**
 * 上传用户头像
 * 使用 FormData 封装文件数据，Content-Type 设为 multipart/form-data
 */
export function uploadAvatar(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/api/user/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
