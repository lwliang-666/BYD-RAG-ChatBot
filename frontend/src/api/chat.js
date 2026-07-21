/**
 * chat.js - 对话相关 API 接口
 * 封装对话列表的增删改查和消息发送等 HTTP 请求
 * 注意：sendMessage 使用原生 fetch 实现 SSE 流式响应，不走 axios
 */
import api from './request'

/** 获取对话列表，支持分页参数 */
export function getConversations(skip = 0, limit = 50) {
  return api.get('/api/chat/conversations', { params: { skip, limit } })
}

/** 创建新对话，可指定初始标题 */
export function createConversation(title = '新对话') {
  return api.post('/api/chat/conversations', { title })
}

/** 获取单个对话详情（含历史消息） */
export function getConversation(id) {
  return api.get(`/api/chat/conversations/${id}`)
}

/** 更新对话信息（如标题、置顶状态） */
export function updateConversation(id, data) {
  return api.put(`/api/chat/conversations/${id}`, data)
}

/** 删除对话 */
export function deleteConversation(id) {
  return api.delete(`/api/chat/conversations/${id}`)
}

/**
 * 发送消息（SSE 流式响应）
 * 使用原生 fetch 而非 axios，以支持 ReadableStream 逐块读取
 * @param {string} conversationId - 对话 ID
 * @param {string} content - 用户输入的消息内容
 * @param {AbortSignal} signal - 用于中断请求的 AbortController 信号
 */
export function sendMessage(conversationId, content, signal) {
  // 从 localStorage 获取访问令牌
  const token = localStorage.getItem('access_token')
  const baseURL = import.meta.env.VITE_API_BASE_URL || ''
  return fetch(`${baseURL}/api/chat/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ content }),
    signal,
  })
}

/**
 * 语音识别：上传音频文件，返回识别文字
 * @param {Blob} audioBlob - 录音产生的音频 Blob
 */
export function speechToText(audioBlob) {
  const token = localStorage.getItem('access_token')
  const baseURL = import.meta.env.VITE_API_BASE_URL || ''
  const formData = new FormData()
  formData.append('file', audioBlob, 'audio.webm')
  return fetch(`${baseURL}/api/chat/speech-to-text`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  })
}
