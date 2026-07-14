<template>
  <div class="chat-layout">
    <!-- 左侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar__header">
        <button class="sidebar__new-btn" @click="handleNewConversation">+ 开启新对话</button>
      </div>
      <div class="sidebar__list">
        <div
          v-for="conv in chatStore.conversations"
          :key="conv.id"
          :class="['sidebar__item', { 'sidebar__item--active': chatStore.currentConversation === conv.id }]"
          @click="chatStore.selectConversation(conv.id)"
          @contextmenu.prevent="openContextMenu($event, conv)"
        >
          <span v-if="conv.is_pinned" class="sidebar__pin-icon">📌</span>
          <span class="sidebar__item-title">{{ conv.title }}</span>
        </div>
      </div>
      <div class="sidebar__footer">
        <AvatarUpload
          :model-value="userStore.avatarUrl"
          @upload="handleAvatarUpload"
        />
        <div class="sidebar__user-info">
          <template v-if="isEditingName">
            <input
              ref="nameInputRef"
              v-model="editingName"
              class="sidebar__name-input"
              @blur="handleNameSave"
              @keydown.enter="handleNameSave"
            />
          </template>
          <template v-else>
            <span class="sidebar__username" @dblclick="startEditName">
              {{ userStore.displayName || userStore.username }}
            </span>
            <button class="sidebar__edit-btn" @click="startEditName">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
            </button>
          </template>
        </div>
        <button class="sidebar__logout" @click="handleLogout">退出</button>
      </div>
    </aside>

    <!-- 右侧主区域 -->
    <main class="chat-main">
      <template v-if="chatStore.currentConversation">
        <div class="chat-main__header">
          <h3 class="chat-main__title">
            {{ currentConvTitle }}
          </h3>
        </div>
        <div class="chat-main__messages" ref="messagesRef">
          <ChatMessage
            v-for="msg in chatStore.messages"
            :key="msg.id"
            :message="msg"
            :avatar-url="userStore.avatarUrl"
          />
          <div v-if="chatStore.streamingContent" class="chat-message chat-message--assistant">
            <div class="chat-message__bot-avatar">AI</div>
            <div class="chat-message__body">
              <div class="chat-message__content" v-html="renderStreaming"></div>
            </div>
          </div>
        </div>
        <ChatInput :disabled="chatStore.isSending" @send="handleSend" />
      </template>
      <template v-else>
        <div class="chat-main__empty">
          <h2>BYD 智能问答助手</h2>
          <p>点击左侧"开启新对话"开始提问</p>
        </div>
      </template>
    </main>

    <!-- 右键菜单 -->
    <div
      v-if="contextMenu.visible"
      class="context-menu"
      :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }"
    >
      <button @click="handleRename">重命名</button>
      <button @click="handleTogglePin">
        {{ contextMenu.conv?.is_pinned ? '取消置顶' : '置顶' }}
      </button>
      <button class="context-menu__danger" @click="handleDelete">删除</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import MarkdownIt from 'markdown-it'
import { useAuthStore } from '../stores/auth'
import { useChatStore } from '../stores/chat'
import { useUserStore } from '../stores/user'
import { sendMessage } from '../api/chat'
import ChatMessage from '../components/ChatMessage.vue'
import ChatInput from '../components/ChatInput.vue'
import AvatarUpload from '../components/AvatarUpload.vue'

const router = useRouter()
const authStore = useAuthStore()
const chatStore = useChatStore()
const userStore = useUserStore()

const messagesRef = ref(null)
const nameInputRef = ref(null)
const isEditingName = ref(false)
const editingName = ref('')

const contextMenu = ref({ visible: false, x: 0, y: 0, conv: null })

const md = new MarkdownIt()

const renderStreaming = computed(() => md.render(chatStore.streamingContent || ''))

const currentConvTitle = computed(() => {
  const conv = chatStore.conversations.find((c) => c.id === chatStore.currentConversation)
  return conv?.title || '新对话'
})

onMounted(async () => {
  await userStore.fetchProfile()
  await chatStore.fetchConversations()
})

document.addEventListener('click', () => {
  contextMenu.value.visible = false
})

watch(
  () => chatStore.messages.length,
  () => {
    nextTick(scrollToBottom)
  }
)

function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

async function handleNewConversation() {
  await chatStore.newConversation()
}

async function handleSend(content) {
  if (!chatStore.currentConversation) return
  chatStore.isSending = true
  chatStore.streamingContent = ''
  chatStore.addMessage('user', content)

  try {
    const response = await sendMessage(chatStore.currentConversation, content)
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let fullContent = ''
    let lastSources = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const text = decoder.decode(value, { stream: true })
      const lines = text.split('\n')

      let currentEvent = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (currentEvent === 'token' && data.content) {
              fullContent += data.content
              chatStore.streamingContent = fullContent
            } else if (currentEvent === 'sources' && data.chunks) {
              lastSources = data.chunks
            } else if (currentEvent === 'done') {
              // stream complete
            }
          } catch {}
        }
      }
    }

    chatStore.addMessage('assistant', fullContent, lastSources ? { chunks: lastSources } : null)
    chatStore.streamingContent = ''
  } catch (e) {
    chatStore.addMessage('assistant', '抱歉，发生了错误，请稍后再试。')
  } finally {
    chatStore.isSending = false
  }
}

function openContextMenu(e, conv) {
  contextMenu.value = { visible: true, x: e.clientX, y: e.clientY, conv }
}

async function handleRename() {
  const conv = contextMenu.value.conv
  if (!conv) return
  const title = prompt('请输入新名称', conv.title)
  if (title && title.trim()) {
    await chatStore.renameConversation(conv.id, title.trim())
  }
  contextMenu.value.visible = false
}

async function handleTogglePin() {
  const conv = contextMenu.value.conv
  if (!conv) return
  await chatStore.togglePin(conv.id, !conv.is_pinned)
  contextMenu.value.visible = false
}

async function handleDelete() {
  const conv = contextMenu.value.conv
  if (!conv) return
  if (confirm('确定删除该对话？')) {
    await chatStore.removeConversation(conv.id)
  }
  contextMenu.value.visible = false
}

function startEditName() {
  editingName.value = userStore.displayName || userStore.username
  isEditingName.value = true
  nextTick(() => nameInputRef.value?.focus())
}

async function handleNameSave() {
  isEditingName.value = false
  const newName = editingName.value.trim()
  if (!newName || newName === userStore.displayName) return
  try {
    await userStore.updateDisplayName(newName)
  } catch {}
}

async function handleAvatarUpload(file) {
  try {
    await userStore.changeAvatar(file)
  } catch {}
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: 100vh;
  background: #f9fafb;
}
.sidebar {
  width: 280px;
  background: #fff;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
}
.sidebar__header {
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
}
.sidebar__new-btn {
  width: 100%;
  padding: 10px;
  background: #4f46e5;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}
.sidebar__new-btn:hover {
  background: #4338ca;
}
.sidebar__list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.sidebar__item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #374151;
  transition: background 0.15s;
}
.sidebar__item:hover {
  background: #f3f4f6;
}
.sidebar__item--active {
  background: #eef2ff;
  color: #4f46e5;
  font-weight: 500;
}
.sidebar__pin-icon {
  font-size: 12px;
}
.sidebar__item-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sidebar__footer {
  padding: 16px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  gap: 10px;
}
.sidebar__user-info {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 4px;
}
.sidebar__username {
  font-size: 14px;
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: default;
}
.sidebar__name-input {
  font-size: 14px;
  border: 1px solid #4f46e5;
  border-radius: 4px;
  padding: 2px 6px;
  outline: none;
  width: 100%;
}
.sidebar__edit-btn {
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
}
.sidebar__edit-btn:hover {
  color: #4f46e5;
}
.sidebar__logout {
  background: none;
  border: none;
  color: #9ca3af;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}
.sidebar__logout:hover {
  color: #ef4444;
  background: #fef2f2;
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chat-main__header {
  padding: 16px 24px;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
}
.chat-main__title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}
.chat-main__messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}
.chat-main__empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
}
.chat-main__empty h2 {
  font-size: 24px;
  font-weight: 700;
  color: #6b7280;
  margin-bottom: 8px;
}
.chat-main__empty p {
  font-size: 14px;
}
.chat-message {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
}
.chat-message--assistant {
  flex-direction: row;
}
.chat-message__bot-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}
.chat-message__body {
  max-width: 70%;
  min-width: 0;
}
.chat-message__content {
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  word-break: break-word;
  background: #f3f4f6;
  color: #1f2937;
  border-bottom-left-radius: 4px;
}
.context-menu {
  position: fixed;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  padding: 4px;
  z-index: 1000;
  min-width: 120px;
}
.context-menu button {
  display: block;
  width: 100%;
  padding: 8px 12px;
  background: none;
  border: none;
  text-align: left;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
  border-radius: 4px;
}
.context-menu button:hover {
  background: #f3f4f6;
}
.context-menu__danger {
  color: #ef4444 !important;
}
.context-menu__danger:hover {
  background: #fef2f2 !important;
}
</style>
