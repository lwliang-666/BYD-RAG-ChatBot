<!--
  ChatMessage.vue - 聊天消息气泡组件
  根据消息角色（user/assistant）渲染不同样式的消息气泡
  支持 Markdown 渲染、代码高亮、引用来源展示、复制、填入和语音播放操作
-->
<template>
  <!-- 根据消息角色应用不同样式：用户消息靠右，AI 消息靠左 -->
  <div :class="['chat-message', `chat-message--${message.role}`]">
    <div class="chat-message__avatar">
      <!-- 用户头像：优先使用自定义头像，否则使用默认头像 -->
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
      <!-- AI 头像：渐变背景 + "AI" 文字 -->
      <div v-else class="chat-message__bot-avatar">AI</div>
    </div>
    <div class="chat-message__body">
      <!-- 消息内容：使用 v-html 渲染 Markdown 转 HTML 后的内容 -->
      <div class="chat-message__content" v-html="renderedContent"></div>
      <!-- 用户消息的操作按钮：复制 / 填入输入框 -->
      <div v-if="message.role === 'user'" class="chat-message__actions">
        <button
          class="chat-message__action-btn"
          :title="copied ? '已复制' : '复制'"
          @click="handleCopy"
        >
          <!-- 复制图标：已复制时显示勾选图标 -->
          <svg v-if="!copied" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <span class="chat-message__action-label">{{ copied ? '已复制' : '复制' }}</span>
        </button>
        <!-- 填入按钮：将消息内容填入输入框，便于重新提问 -->
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
      <!-- AI 消息的操作按钮：语音播放 -->
      <div v-if="message.role === 'assistant'" class="chat-message__actions chat-message__actions--assistant">
        <button
          :class="['chat-message__action-btn', { 'chat-message__action-btn--playing': isPlaying }]"
          :title="isPlaying ? '停止播放' : '语音播放'"
          @click="toggleSpeech"
        >
          <!-- 播放图标 -->
          <svg v-if="!isPlaying" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
          </svg>
          <!-- 停止图标 -->
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="6" width="12" height="12" rx="2"/>
          </svg>
          <span class="chat-message__action-label">{{ isPlaying ? '停止' : '播放' }}</span>
        </button>
      </div>
      <!-- 引用来源区域：展示 RAG 检索到的文档片段 -->
      <div v-if="message.sources && message.sources.chunks?.length" class="chat-message__sources">
        <button class="chat-message__sources-toggle" @click="showSources = !showSources">
          {{ showSources ? '收起引用' : '查看引用' }} ({{ message.sources.chunks.length }})
        </button>
        <!-- 引用来源列表 -->
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
import { ref, computed, onUnmounted } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

// 组件属性
const props = defineProps({
  message: { type: Object, required: true },  // 消息对象，包含 role、content、sources 等
  avatarUrl: { type: String, default: '' },    // 用户头像 URL
})

// 组件事件
const emit = defineEmits(['fill'])

// 引用来源展开/收起状态
const showSources = ref(false)
// 复制按钮状态
const copied = ref(false)
let copyTimer = null

// 语音播放状态
const isPlaying = ref(false)

/**
 * 去除 Markdown 标记，提取纯文本供语音朗读
 * 去除代码块、行内代码、链接、图片、加粗/斜体等标记
 */
function stripMarkdown(mdText) {
  return mdText
    .replace(/```[\s\S]*?```/g, '')            // 去除代码块
    .replace(/`([^`]+)`/g, '$1')               // 去除行内代码
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')   // 链接只保留文字
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '')    // 去除图片
    .replace(/(\*\*|__)(.*?)\1/g, '$2')        // 去除加粗
    .replace(/(\*|_)(.*?)\1/g, '$2')           // 去除斜体
    .replace(/^#{1,6}\s+/gm, '')               // 去除标题标记
    .replace(/^[-*+]\s+/gm, '')                // 去除无序列表标记
    .replace(/^\d+\.\s+/gm, '')                // 去除有序列表标记
    .replace(/^>\s+/gm, '')                    // 去除引用标记
    .replace(/\n{2,}/g, '\n')                  // 多个换行合并
    .trim()
}

/** 获取最佳中文语音（按质量优先级选择） */
function getBestChineseVoice() {
  const voices = window.speechSynthesis.getVoices()
  if (!voices.length) return null

  // 优先级：高质量中文语音 > zh-CN 精确匹配 > zh 前缀
  const priorities = [
    // macOS Neural 中文女声（音质最佳）
    v => v.name === 'Shelley (中文（中国大陆）)',
    v => v.name === 'Sandy (中文（中国大陆）)',
    v => v.name === 'Flo (中文（中国大陆）)',
    // Windows 高质量中文语音
    v => v.name.includes('Huihui') || v.name.includes('Kangkang'),
    // Google 中文语音（Chrome）
    v => v.name.includes('Google') && v.lang === 'zh-CN',
    // zh-CN 精确匹配
    v => v.lang === 'zh-CN',
    // zh 前缀兜底
    v => v.lang.startsWith('zh'),
  ]

  for (const matcher of priorities) {
    const voice = voices.find(matcher)
    if (voice) return voice
  }
  return null
}

/** 切换语音播放状态 */
function toggleSpeech() {
  if (isPlaying.value) {
    window.speechSynthesis.cancel()
    isPlaying.value = false
    return
  }

  const plainText = stripMarkdown(props.message.content || '')
  if (!plainText) return

  const utterance = new SpeechSynthesisUtterance(plainText)
  utterance.lang = 'zh-CN'
  utterance.rate = 0.9
  utterance.pitch = 1.0

  const voice = getBestChineseVoice()
  if (voice) {
    utterance.voice = voice
  }

  utterance.onend = () => {
    isPlaying.value = false
  }
  utterance.onerror = () => {
    isPlaying.value = false
  }

  // 停止其他正在播放的语音
  window.speechSynthesis.cancel()
  isPlaying.value = true
  window.speechSynthesis.speak(utterance)
}

// 组件卸载时停止播放
onUnmounted(() => {
  if (isPlaying.value) {
    window.speechSynthesis.cancel()
  }
})

/**
 * 复制消息内容到剪贴板
 * 优先使用 Clipboard API，非 HTTPS 环境下使用 execCommand 兜底
 */
async function handleCopy() {
  const text = props.message.content || ''
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      // 非 HTTPS 环境：创建临时 textarea 执行复制
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    // 显示已复制状态，1.5 秒后恢复
    copied.value = true
    if (copyTimer) clearTimeout(copyTimer)
    copyTimer = setTimeout(() => {
      copied.value = false
    }, 1500)
  } catch (e) {
    // 复制失败时不显示成功态
  }
}

/** 触发 fill 事件，将消息内容填入父组件的输入框 */
function handleFill() {
  emit('fill', props.message.content || '')
}

// Markdown 渲染器：配置代码高亮插件
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

// 计算属性：将消息内容渲染为 HTML
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
/* 用户消息气泡样式 */
.chat-message--user .chat-message__content {
  background: #4f46e5;
  color: #fff;
  border-bottom-right-radius: 4px;
}
/* AI 消息气泡样式 */
.chat-message--assistant .chat-message__content {
  background: #f3f4f6;
  color: #1f2937;
  border-bottom-left-radius: 4px;
}
/* 代码块样式 */
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
/* 操作按钮：默认隐藏，悬停时显示 */
.chat-message__actions {
  display: flex;
  gap: 6px;
  margin-top: 6px;
  justify-content: flex-end;
  opacity: 0;
  transition: opacity 0.2s;
}
.chat-message--user:hover .chat-message__actions {
  opacity: 1;
}
/* AI 消息操作按钮始终可见 */
.chat-message__actions--assistant {
  justify-content: flex-start;
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
/* 播放中按钮高亮样式 */
.chat-message__action-btn--playing {
  color: #6d28d9;
  border-color: #8b5cf6;
  background: #ede9fe;
}
.chat-message__action-btn--playing:hover {
  color: #4c1d95;
  border-color: #7c3aed;
  background: #ddd6fe;
}
.chat-message__action-label {
  font-size: 12px;
}
/* 引用来源样式 */
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
