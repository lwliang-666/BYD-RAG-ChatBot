<template>
  <div :class="['chat-message', `chat-message--${message.role}`]">
    <div class="chat-message__avatar">
      <img
        v-if="message.role === 'user' && avatarUrl"
        :src="avatarUrl"
        alt="avatar"
        class="chat-message__avatar-img"
      />
      <img
        v-else-if="message.role === 'user'"
        src="../assets/default-avatar.svg"
        alt="avatar"
        class="chat-message__avatar-img"
      />
      <div v-else class="chat-message__bot-avatar">AI</div>
    </div>
    <div class="chat-message__body">
      <div class="chat-message__content" v-html="renderedContent"></div>
      <!-- 用户消息的操作按钮：复制 / 填入输入框 -->
      <div v-if="message.role === 'user'" class="chat-message__actions">
        <button
          class="chat-message__action-btn"
          :title="copied ? '已复制' : '复制'"
          @click="handleCopy"
        >
          <svg v-if="!copied" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <span class="chat-message__action-label">{{ copied ? '已复制' : '复制' }}</span>
        </button>
        <button
          class="chat-message__action-btn"
          title="填入输入框"
          @click="handleFill"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 5v14"/>
            <polyline points="19 12 12 19 5 12"/>
          </svg>
          <span class="chat-message__action-label">填入</span>
        </button>
      </div>
      <div v-if="message.sources && message.sources.chunks?.length" class="chat-message__sources">
        <button class="chat-message__sources-toggle" @click="showSources = !showSources">
          {{ showSources ? '收起引用' : '查看引用' }} ({{ message.sources.chunks.length }})
        </button>
        <div v-if="showSources" class="chat-message__sources-list">
          <div
            v-for="(chunk, idx) in message.sources.chunks"
            :key="idx"
            class="chat-message__source-item"
          >
            <span class="chat-message__source-page">
              第{{ chunk.metadata?.page_number || '未知' }}页
            </span>
            <span class="chat-message__source-text">{{ chunk.content }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

const props = defineProps({
  message: { type: Object, required: true },
  avatarUrl: { type: String, default: '' },
})

const emit = defineEmits(['fill'])

const showSources = ref(false)
const copied = ref(false)
let copyTimer = null

// 复制到剪贴板，兼容非 https 场景（使用 execCommand 兜底）
async function handleCopy() {
  const text = props.message.content || ''
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    copied.value = true
    if (copyTimer) clearTimeout(copyTimer)
    copyTimer = setTimeout(() => {
      copied.value = false
    }, 1500)
  } catch (e) {
    // 复制失败时不显示成功态
  }
}

function handleFill() {
  emit('fill', props.message.content || '')
}

const md = new MarkdownIt({
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang }).value
      } catch {}
    }
    return ''
  },
})

const renderedContent = computed(() => md.render(props.message.content || ''))
</script>

<style scoped>
.chat-message {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
}
.chat-message--user {
  flex-direction: row-reverse;
}
.chat-message__avatar {
  flex-shrink: 0;
}
.chat-message__avatar-img {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  object-fit: cover;
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
}
.chat-message__body {
  max-width: 70%;
  min-width: 0;
}
.chat-message--user .chat-message__body {
  align-items: flex-end;
}
.chat-message__content {
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  word-break: break-word;
}
.chat-message--user .chat-message__content {
  background: #4f46e5;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.chat-message--assistant .chat-message__content {
  background: #f3f4f6;
  color: #1f2937;
  border-bottom-left-radius: 4px;
}
.chat-message__content :deep(pre) {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}
.chat-message__content :deep(code) {
  font-size: 13px;
}
.chat-message__content :deep(p) {
  margin: 4px 0;
}
.chat-message__actions {
  display: flex;
  gap: 6px;
  margin-top: 6px;
  justify-content: flex-end;
  opacity: 0;
  transition: opacity 0.2s;
}
/* 用户气泡悬停时才显示操作按钮 */
.chat-message--user:hover .chat-message__actions {
  opacity: 1;
}
.chat-message__action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  font-size: 12px;
  color: #6b7280;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  cursor: pointer;
  line-height: 1;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.chat-message__action-btn:hover {
  color: #4f46e5;
  border-color: #c7d2fe;
  background: #eef2ff;
}
.chat-message__action-label {
  font-size: 12px;
}
.chat-message__sources {
  margin-top: 8px;
}
.chat-message__sources-toggle {
  font-size: 12px;
  color: #6b7280;
  background: none;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  padding: 2px 8px;
  cursor: pointer;
}
.chat-message__sources-toggle:hover {
  color: #4f46e5;
  border-color: #4f46e5;
}
.chat-message__sources-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.chat-message__source-item {
  font-size: 12px;
  padding: 8px;
  background: #f9fafb;
  border-radius: 6px;
  border-left: 3px solid #4f46e5;
}
.chat-message__source-page {
  font-weight: 600;
  color: #4f46e5;
  margin-right: 8px;
}
.chat-message__source-text {
  color: #6b7280;
}
</style>
