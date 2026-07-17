<!--
  ChatView.vue - 聊天主页面
  包含左侧对话列表边栏和右侧消息区域，是应用的核心交互页面
  功能：对话管理（新建/重命名/置顶/删除）、消息发送与流式接收、用户资料编辑
-->
<template>
  <div class="chat-layout">
    <!-- 左侧边栏：对话列表 + 用户信息 -->
    <aside class="sidebar">
      <div class="sidebar__header">
        <h2 class="sidebar__title">比亚迪驱逐舰05 智能问答助手</h2>
        <button class="sidebar__new-btn" @click="handleNewConversation">+ 开启新对话</button>
      </div>
      <!-- 对话列表 -->
      <div class="sidebar__list">
        <div
          v-for="conv in chatStore.conversations"
          :key="conv.id"
          :class="['sidebar__item', { 'sidebar__item--active': chatStore.currentConversation === conv.id }]"
          @click="chatStore.selectConversation(conv.id)"
        >
          <!-- 置顶图标 -->
          <span v-if="conv.is_pinned" class="sidebar__pin-icon">📌</span>
          <!-- 重命名编辑模式 -->
          <template v-if="renamingConvId === conv.id">
            <input
              ref="renameInputRef"
              v-model="renamingTitle"
              class="sidebar__rename-input"
              @keydown.enter="confirmRename"
              @keydown.escape="cancelRename"
              @blur="confirmRename"
              @click.stop
            />
          </template>
          <!-- 正常显示模式 -->
          <template v-else>
            <span class="sidebar__item-title">{{ conv.title }}</span>
            <!-- 更多操作按钮：点击弹出上下文菜单 -->
            <button class="sidebar__item-more" @click.stop="openContextMenu($event, conv)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <circle cx="5" cy="12" r="2"/>
                <circle cx="12" cy="12" r="2"/>
                <circle cx="19" cy="12" r="2"/>
              </svg>
            </button>
          </template>
        </div>
      </div>
      <!-- 底部用户信息区：头像 + 显示名 + 退出按钮 -->
      <div class="sidebar__footer">
        <AvatarUpload
          :model-value="userStore.avatarUrl"
          @upload="handleAvatarUpload"
        />
        <div class="sidebar__user-info">
          <!-- 编辑显示名模式 -->
          <template v-if="isEditingName">
            <input
              ref="nameInputRef"
              v-model="editingName"
              class="sidebar__name-input"
              @blur="handleNameSave"
              @keydown.enter="handleNameSave"
            />
          </template>
          <!-- 显示名展示模式：双击可编辑 -->
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

    <!-- 右侧主区域：消息展示 + 输入框 -->
    <main class="chat-main">
      <!-- 已选中对话时显示消息区域 -->
      <template v-if="chatStore.currentConversation">
        <div class="chat-main__header">
          <h3 class="chat-main__title">
            {{ currentConvTitle }}
          </h3>
        </div>
        <!-- 消息列表 -->
        <div class="chat-main__messages" ref="messagesRef">
          <ChatMessage
            v-for="msg in chatStore.messages"
            :key="msg.id"
            :message="msg"
            :avatar-url="userStore.avatarUrl"
            @fill="handleFillInput"
          />
          <!-- 流式响应中的实时内容 -->
          <div v-if="chatStore.streamingContent" class="chat-message chat-message--assistant">
            <div class="chat-message__bot-avatar">AI</div>
            <div class="chat-message__body">
              <div class="chat-message__content" v-html="renderStreaming"></div>
            </div>
          </div>
          <!-- 等待响应时的加载动画 -->
          <div v-else-if="chatStore.isSending" class="chat-message chat-message--assistant">
            <div class="chat-message__bot-avatar">AI</div>
            <div class="chat-message__body">
              <div class="chat-message__content chat-message__loading">
                <span class="loading-dot"></span>
                <span class="loading-dot"></span>
                <span class="loading-dot"></span>
              </div>
            </div>
          </div>
        </div>
        <ChatInput ref="chatInputRef" :disabled="chatStore.isSending" :is-streaming="chatStore.isSending" :remaining-questions="chatStore.remainingQuestions" @send="handleSend" @stop="handleStop" />
      </template>
      <!-- 未选中对话时显示空状态提示 -->
      <template v-else>
        <div class="chat-main__empty">
          <h2>比亚迪驱逐舰05 智能问答助手</h2>
          <p>点击左侧"开启新对话"开始提问</p>
        </div>
      </template>
    </main>

    <!-- 右键操作菜单：重命名 / 置顶 / 删除 -->
    <div
      v-if="contextMenu.visible"
      class="context-menu"
      :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }"
    >
      <button @click="handleRename">
        <svg class="context-menu__icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
        </svg>
        重命名
      </button>
      <button @click="handleTogglePin">
        <svg class="context-menu__icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 17v5"/>
          <path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V5a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2z"/>
        </svg>
        {{ contextMenu.conv?.is_pinned ? '取消置顶' : '置顶' }}
      </button>
      <button class="context-menu__danger" @click="handleDelete">
        <svg class="context-menu__icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="3 6 5 6 21 6"/>
          <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
          <path d="M10 11v6"/>
          <path d="M14 11v6"/>
          <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
        </svg>
        删除
      </button>
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

// DOM 引用
const messagesRef = ref(null)       // 消息列表容器，用于自动滚动到底部
const chatInputRef = ref(null)      // 输入框组件引用
const nameInputRef = ref(null)      // 显示名编辑输入框引用

// 用户名编辑状态
const isEditingName = ref(false)
const editingName = ref('')

// 右键菜单状态
const contextMenu = ref({ visible: false, x: 0, y: 0, conv: null })

// 对话重命名状态
const renamingConvId = ref(null)
const renamingTitle = ref('')
const renameInputRef = ref(null)
let renameConfirming = false  // 防止 blur 和 enter 重复触发确认

// Markdown 渲染器（用于流式内容的实时渲染）
const md = new MarkdownIt()

/** 流式内容的 Markdown 渲染结果 */
const renderStreaming = computed(() => md.render(chatStore.streamingContent || ''))

/** 当前对话标题 */
const currentConvTitle = computed(() => {
  const conv = chatStore.conversations.find((c) => c.id === chatStore.currentConversation)
  return conv?.title || '新对话'
})

// 页面挂载时加载用户资料和对话列表
onMounted(async () => {
  await userStore.fetchProfile()
  await chatStore.fetchConversations()
})

// 全局点击事件：关闭右键菜单
document.addEventListener('click', () => {
  contextMenu.value.visible = false
})

// 监听消息数量变化，自动滚动到底部
watch(
  () => chatStore.messages.length,
  () => {
    nextTick(scrollToBottom)
  }
)

/** 滚动消息列表到底部 */
function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

/** 创建新对话并自动聚焦输入框 */
async function handleNewConversation() {
  await chatStore.newConversation()
  nextTick(() => chatInputRef.value?.focus())
}

/**
 * 发送消息并处理 SSE 流式响应
 * 解析服务端推送的 token/sources/done 事件，实时更新流式内容
 */
async function handleSend(content) {
  if (!chatStore.currentConversation) return
  chatStore.isSending = true
  chatStore.streamingContent = ''

  // 创建 AbortController，用于用户主动中断流式请求
  const controller = new AbortController()
  chatStore.abortController = controller

  // 先将用户消息添加到消息列表
  chatStore.addMessage('user', content)

  try {
    // 发起 SSE 流式请求
    const response = await sendMessage(chatStore.currentConversation, content, controller.signal)

    // 处理 429 提问次数超限
    if (response.status === 429) {
      const errorData = await response.json()
      chatStore.remainingQuestions = 0
      chatStore.addMessage('assistant', '今日提问次数已用完，请明天再来。')
      return
    }
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let fullContent = ''
    let lastSources = null

    // 逐块读取流式响应
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const text = decoder.decode(value, { stream: true })
      const lines = text.split('\n')

      // 解析 SSE 事件格式
      let currentEvent = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          // 事件类型行
          currentEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          // 事件数据行
          try {
            const data = JSON.parse(line.slice(6))
            if (currentEvent === 'token' && data.content) {
              // token 事件：追加流式文本内容
              fullContent += data.content
              chatStore.streamingContent = fullContent
            } else if (currentEvent === 'sources' && data.chunks) {
              // sources 事件：保存 RAG 检索的引用来源
              lastSources = data.chunks
            } else if (currentEvent === 'done') {
              // done 事件：流式响应完成，提取剩余提问次数
              if (data.remaining) {
                chatStore.remainingQuestions = data.remaining.user_remaining
              }
            }
          } catch {}
        }
      }
    }

    // 流式响应完成，将完整内容作为正式消息保存
    chatStore.addMessage('assistant', fullContent, lastSources ? { chunks: lastSources } : null)
    chatStore.streamingContent = ''
  } catch (e) {
    if (e.name === 'AbortError') {
      // 用户主动停止，保存已接收的部分内容
      if (chatStore.streamingContent) {
        chatStore.addMessage('assistant', chatStore.streamingContent + '\n\n*[对话已停止]*')
      }
      chatStore.streamingContent = ''
    } else {
      // 其他错误，显示错误提示
      chatStore.addMessage('assistant', '抱歉，发生了错误，请稍后再试。')
      chatStore.streamingContent = ''
    }
  } finally {
    chatStore.isSending = false
    chatStore.abortController = null
    // 刷新对话列表以同步后端自动设置的标题
    chatStore.fetchConversations()
  }
}

/** 停止流式响应：中断正在进行的请求 */
function handleStop() {
  if (chatStore.abortController) {
    chatStore.abortController.abort()
  }
}

/** 将用户历史消息填入输入框，便于重新提问或编辑 */
function handleFillInput(content) {
  chatInputRef.value?.setText(content)
}

/** 打开对话右键操作菜单 */
function openContextMenu(e, conv) {
  const rect = e.currentTarget.getBoundingClientRect()
  contextMenu.value = {
    visible: true,
    x: rect.right - 140,  // 菜单右对齐到按钮右边缘
    y: rect.bottom + 4,   // 菜单出现在按钮下方
    conv,
  }
}

/** 进入对话重命名模式 */
async function handleRename() {
  const conv = contextMenu.value.conv
  contextMenu.value.visible = false
  if (!conv) return
  renamingConvId.value = conv.id
  renamingTitle.value = conv.title
  await nextTick()
  // 聚焦重命名输入框
  const inputs = document.querySelectorAll('.sidebar__rename-input')
  if (inputs.length) inputs[inputs.length - 1].focus()
}

/** 确认重命名对话 */
async function confirmRename() {
  // 防止 blur 和 enter 重复触发
  if (renameConfirming) return
  renameConfirming = true
  const convId = renamingConvId.value
  const title = renamingTitle.value.trim()
  renamingConvId.value = null
  // 标题有效且发生变化时才调用接口更新
  if (convId && title) {
    const conv = chatStore.conversations.find((c) => c.id === convId)
    if (conv && conv.title !== title) {
      await chatStore.renameConversation(convId, title)
    }
  }
  renameConfirming = false
}

/** 取消重命名 */
function cancelRename() {
  renamingConvId.value = null
}

/** 切换对话置顶状态 */
async function handleTogglePin() {
  const conv = contextMenu.value.conv
  if (!conv) return
  await chatStore.togglePin(conv.id, !conv.is_pinned)
  contextMenu.value.visible = false
}

/** 删除对话（需用户确认） */
async function handleDelete() {
  const conv = contextMenu.value.conv
  if (!conv) return
  if (confirm('确定删除该对话？')) {
    await chatStore.removeConversation(conv.id)
  }
  contextMenu.value.visible = false
}

/** 进入显示名编辑模式 */
function startEditName() {
  editingName.value = userStore.displayName || userStore.username
  isEditingName.value = true
  nextTick(() => nameInputRef.value?.focus())
}

/** 保存显示名修改 */
async function handleNameSave() {
  isEditingName.value = false
  const newName = editingName.value.trim()
  if (!newName || newName === userStore.displayName) return
  try {
    await userStore.updateDisplayName(newName)
  } catch {}
}

/** 处理头像上传 */
async function handleAvatarUpload(file) {
  try {
    await userStore.changeAvatar(file)
  } catch {}
}

/** 退出登录 */
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
.sidebar__title {
  font-size: 14px;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 12px 0;
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
  flex: 1;
  min-width: 0;
}
.sidebar__item-more {
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  padding: 2px;
  display: none;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  flex-shrink: 0;
}
/* 悬停时显示更多操作按钮 */
.sidebar__item:hover .sidebar__item-more {
  display: flex;
}
.sidebar__item-more:hover {
  color: #374151;
  background: #e5e7eb;
}
.sidebar__rename-input {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  border: 1px solid #4f46e5;
  border-radius: 4px;
  padding: 2px 6px;
  outline: none;
  font-family: inherit;
}
.sidebar__footer {
  height: 75px;
  padding: 0 16px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
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
/* 流式响应中的 AI 消息样式 */
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
/* 加载动画：三个跳动的圆点 */
.chat-message__loading {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 18px;
}
.loading-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #9ca3af;
  animation: loading-bounce 1.4s ease-in-out infinite;
}
.loading-dot:nth-child(2) {
  animation-delay: 0.16s;
}
.loading-dot:nth-child(3) {
  animation-delay: 0.32s;
}
@keyframes loading-bounce {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
/* 右键菜单样式 */
.context-menu {
  position: fixed;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  padding: 4px;
  z-index: 1000;
  min-width: 140px;
}
.context-menu button {
  display: flex;
  align-items: center;
  gap: 8px;
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
.context-menu__icon {
  flex-shrink: 0;
}
/* 删除按钮危险样式 */
.context-menu__danger {
  color: #ef4444 !important;
}
.context-menu__danger:hover {
  background: #fef2f2 !important;
}
</style>
