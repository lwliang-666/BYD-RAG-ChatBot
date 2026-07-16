/**
 * stores/chat.js - 对话状态管理
 * 管理对话列表、当前对话、消息记录和流式响应状态
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getConversations, createConversation, getConversation,
  updateConversation, deleteConversation,
} from '../api/chat'

export const useChatStore = defineStore('chat', () => {
  // 对话列表
  const conversations = ref([])
  // 当前选中的对话 ID
  const currentConversation = ref(null)
  // 当前对话的消息列表
  const messages = ref([])
  // 加载状态标记
  const isLoading = ref(false)
  // 发送中状态标记（包含流式响应期间）
  const isSending = ref(false)
  // 流式响应的实时内容（用于逐字渲染）
  const streamingContent = ref('')
  // AbortController 引用，用于中断流式请求
  const abortController = ref(null)

  /** 获取对话列表 */
  async function fetchConversations() {
    const res = await getConversations()
    conversations.value = res.data
  }

  /** 创建新对话并自动选中 */
  async function newConversation() {
    const res = await createConversation()
    conversations.value.unshift(res.data)
    currentConversation.value = res.data.id
    messages.value = []
  }

  /** 选中对话并加载其消息记录 */
  async function selectConversation(id) {
    isLoading.value = true
    try {
      const res = await getConversation(id)
      currentConversation.value = id
      messages.value = res.data.messages || []
    } finally {
      isLoading.value = false
    }
  }

  /** 重命名对话标题 */
  async function renameConversation(id, title) {
    await updateConversation(id, { title })
    // 同步更新本地对话列表中的标题
    const conv = conversations.value.find((c) => c.id === id)
    if (conv) conv.title = title
  }

  /**
   * 切换对话置顶状态
   * 更新后重新排序：置顶对话优先，其次按更新时间降序
   */
  async function togglePin(id, isPinned) {
    await updateConversation(id, { is_pinned: isPinned })
    const conv = conversations.value.find((c) => c.id === id)
    if (conv) conv.is_pinned = isPinned
    // 置顶优先，同级别按更新时间排序
    conversations.value.sort((a, b) => {
      if (a.is_pinned !== b.is_pinned) return b.is_pinned ? 1 : -1
      return new Date(b.updated_at) - new Date(a.updated_at)
    })
  }

  /** 删除对话，若删除的是当前对话则清空消息区 */
  async function removeConversation(id) {
    await deleteConversation(id)
    conversations.value = conversations.value.filter((c) => c.id !== id)
    if (currentConversation.value === id) {
      currentConversation.value = null
      messages.value = []
    }
  }

  /** 向当前对话追加一条消息 */
  function addMessage(role, content, sources = null) {
    messages.value.push({ role, content, sources, created_at: new Date().toISOString() })
  }

  return {
    conversations, currentConversation, messages,
    isLoading, isSending, streamingContent, abortController,
    fetchConversations, newConversation, selectConversation,
    renameConversation, togglePin, removeConversation, addMessage,
  }
})
