import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getConversations, createConversation, getConversation,
  updateConversation, deleteConversation,
} from '../api/chat'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref([])
  const currentConversation = ref(null)
  const messages = ref([])
  const isLoading = ref(false)
  const isSending = ref(false)
  const streamingContent = ref('')
  const abortController = ref(null)

  async function fetchConversations() {
    const res = await getConversations()
    conversations.value = res.data
  }

  async function newConversation() {
    const res = await createConversation()
    conversations.value.unshift(res.data)
    currentConversation.value = res.data.id
    messages.value = []
  }

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

  async function renameConversation(id, title) {
    await updateConversation(id, { title })
    const conv = conversations.value.find((c) => c.id === id)
    if (conv) conv.title = title
  }

  async function togglePin(id, isPinned) {
    await updateConversation(id, { is_pinned: isPinned })
    const conv = conversations.value.find((c) => c.id === id)
    if (conv) conv.is_pinned = isPinned
    conversations.value.sort((a, b) => {
      if (a.is_pinned !== b.is_pinned) return b.is_pinned ? 1 : -1
      return new Date(b.updated_at) - new Date(a.updated_at)
    })
  }

  async function removeConversation(id) {
    await deleteConversation(id)
    conversations.value = conversations.value.filter((c) => c.id !== id)
    if (currentConversation.value === id) {
      currentConversation.value = null
      messages.value = []
    }
  }

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
