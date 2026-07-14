import api from './request'

export function getProfile() {
  return api.get('/api/user/profile')
}

export function updateProfile(data) {
  return api.put('/api/user/profile', data)
}

export function updateUsername(username) {
  return api.put('/api/user/username', { username })
}

export function uploadAvatar(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/api/user/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
