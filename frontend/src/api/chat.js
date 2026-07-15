import api from './request'

export function getConversations(skip = 0, limit = 50) {
  return api.get('/api/chat/conversations', { params: { skip, limit } })
}

export function createConversation(title = '新对话') {
  return api.post('/api/chat/conversations', { title })
}

export function getConversation(id) {
  return api.get(`/api/chat/conversations/${id}`)
}

export function updateConversation(id, data) {
  return api.put(`/api/chat/conversations/${id}`, data)
}

export function deleteConversation(id) {
  return api.delete(`/api/chat/conversations/${id}`)
}

export function sendMessage(conversationId, content, signal) {
  const token = localStorage.getItem('access_token')
  return fetch(`/api/chat/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ content }),
    signal,
  })
}
