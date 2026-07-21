<!--
  ChatInput.vue - 聊天输入框组件
  提供消息输入、发送、停止流式响应、一键清空、语音输入等功能
  语音输入使用 MediaRecorder 录音，上传后端讯飞语音识别 API 转文字
-->
<template>
  <div class="chat-input">
    <div class="chat-input__row">
      <!-- 消息输入框：支持自动高度调整和 Enter 快捷发送 -->
      <textarea
        ref="textareaRef"
        v-model="text"
        class="chat-input__textarea"
        :placeholder="micPlaceholder"
        rows="1"
        :disabled="disabled || remainingQuestions === 0"
        @keydown.enter.exact.prevent="handleSend"
        @input="autoResize"
      ></textarea>
      <!-- 清空按钮：输入框有内容时显示 -->
      <button
        v-if="text.trim()"
        class="chat-input__clear"
        title="清空输入"
        @click="handleClear"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
      <!-- 语音输入按钮：MediaRecorder 录音 + 后端讯飞识别 -->
      <button
        :class="['chat-input__mic', { 'chat-input__mic--active': micState === 'recording' || micState === 'uploading' }]"
        :title="micTitle"
        :disabled="micDisabled"
        @click="toggleMic"
      >
        <!-- 麦克风图标 -->
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" y1="19" x2="12" y2="23"/>
          <line x1="8" y1="23" x2="16" y2="23"/>
        </svg>
      </button>
      <!-- 发送按钮：非流式状态下显示 -->
      <button
        v-if="!isStreaming"
        class="chat-input__send"
        :disabled="disabled || !text.trim() || remainingQuestions === 0"
        @click="handleSend"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
        </svg>
      </button>
      <!-- 停止按钮：流式响应进行中显示，用于中断生成 -->
      <button
        v-else
        class="chat-input__stop"
        @click="handleStop"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
          <rect x="6" y="6" width="12" height="12" rx="2"/>
        </svg>
      </button>
    </div>
    <!-- 剩余提问次数提示 -->
    <div v-if="remainingQuestions !== null" class="chat-input__hint">
      <span v-if="remainingQuestions > 0" class="chat-input__remaining">今日剩余提问次数: {{ remainingQuestions }}</span>
      <span v-else class="chat-input__remaining chat-input__remaining--exhausted">今日提问次数已用完</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onUnmounted } from 'vue'
import { speechToText } from '../api/chat'

// 组件属性
const props = defineProps({
  disabled: { type: Boolean, default: false },    // 是否禁用输入
  isStreaming: { type: Boolean, default: false },  // 是否正在流式响应中
  remainingQuestions: { type: Number, default: null },  // 今日剩余提问次数
})

// 组件事件
const emit = defineEmits(['send', 'stop'])

// 输入框文本内容和 DOM 引用
const text = ref('')
const textareaRef = ref(null)

// 语音输入状态：idle / recording / uploading
const micState = ref('idle')
let mediaRecorder = null
let audioChunks = []

/** 麦克风按钮是否禁用 */
const micDisabled = computed(() => {
  if (props.disabled || props.remainingQuestions === 0) return true
  return false
})

/** 麦克风按钮提示文字 */
const micTitle = computed(() => {
  if (micState.value === 'recording') return '停止录音'
  if (micState.value === 'uploading') return '识别中...'
  return '语音输入'
})

/** 输入框 placeholder */
const micPlaceholder = computed(() => {
  if (micState.value === 'recording') return '正在录音，点击麦克风停止...'
  if (micState.value === 'uploading') return '正在识别语音...'
  return '输入您的问题...'
})

/** 切换麦克风状态 */
async function toggleMic() {
  if (micState.value === 'recording') {
    stopRecording()
  } else if (micState.value === 'idle') {
    startRecording()
  }
  // uploading 状态下不响应点击
}

/** 开始录音 */
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioChunks = []
    mediaRecorder = new MediaRecorder(stream)

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data)
      }
    }

    mediaRecorder.onstop = async () => {
      // 停止所有音轨
      stream.getTracks().forEach(track => track.stop())

      if (audioChunks.length === 0) {
        micState.value = 'idle'
        return
      }

      // 生成音频 Blob 并上传
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })
      await uploadAndRecognize(audioBlob)
    }

    mediaRecorder.start()
    micState.value = 'recording'
  } catch (e) {
    console.warn('麦克风启动失败:', e)
    micState.value = 'idle'
  }
}

/** 停止录音 */
function stopRecording() {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop()
  }
  micState.value = 'uploading'
}

/** 上传音频并识别 */
async function uploadAndRecognize(audioBlob) {
  micState.value = 'uploading'
  try {
    const data = await speechToText(audioBlob)
    if (data.text) {
      text.value += data.text
      nextTick(autoResize)
    }
  } catch (e) {
    console.warn('语音识别异常:', e)
  } finally {
    micState.value = 'idle'
    mediaRecorder = null
    audioChunks = []
  }
}

// 组件卸载时停止录音
onUnmounted(() => {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop()
  }
})

/** 发送消息：校验内容非空且剩余次数充足后触发 send 事件，并清空输入框 */
function handleSend() {
  if (!text.value.trim() || props.disabled || props.remainingQuestions === 0) return
  emit('send', text.value.trim())
  text.value = ''
  // 清空后重新计算高度
  nextTick(autoResize)
}

/** 停止流式响应 */
function handleStop() {
  emit('stop')
}

/** 清空输入框内容，并重新聚焦 */
function handleClear() {
  text.value = ''
  nextTick(() => {
    autoResize()
    textareaRef.value?.focus()
  })
}

/** 自动调整输入框高度：根据内容撑开，最大高度 150px */
function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 150) + 'px'
}

/** 供父组件调用：写入内容并聚焦输入框 */
function setText(value) {
  text.value = value ?? ''
  nextTick(() => {
    autoResize()
    if (textareaRef.value) {
      textareaRef.value.focus()
      // 光标定位到末尾，便于继续编辑
      const len = textareaRef.value.value.length
      textareaRef.value.setSelectionRange(len, len)
    }
  })
}

/** 供父组件调用：聚焦输入框 */
function focus() {
  textareaRef.value?.focus()
}

// 暴露方法供父组件通过 ref 调用
defineExpose({ setText, focus })
</script>

<style scoped>
.chat-input {
    min-height: 75px;
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 16px 24px 8px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}
.chat-input__row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.chat-input__textarea {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.5;
  resize: none;
  outline: none;
  font-family: inherit;
  transition: border-color 0.2s;
  scrollbar-width: none;
}
.chat-input__textarea::-webkit-scrollbar {
  display: none;
}
.chat-input__textarea:focus {
  border-color: #4f46e5;
}
.chat-input__textarea:disabled {
  background: #f9fafb;
  cursor: not-allowed;
}
.chat-input__clear {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #9ca3af;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
  flex-shrink: 0;
}
.chat-input__clear:hover {
  color: #ef4444;
  border-color: #fca5a5;
  background: #fef2f2;
}
.chat-input__mic {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #9ca3af;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
  flex-shrink: 0;
}
.chat-input__mic:hover:not(:disabled) {
  color: #4f46e5;
  border-color: #c7d2fe;
  background: #eef2ff;
}
.chat-input__mic:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
/* 录音中/上传中状态：红色脉冲动画 */
.chat-input__mic--active {
  color: #fff;
  background: #ef4444;
  border-color: #ef4444;
  animation: mic-pulse 1.5s ease-in-out infinite;
}
.chat-input__mic--active:hover {
  color: #fff;
  background: #dc2626;
  border-color: #dc2626;
}
@keyframes mic-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(239, 68, 68, 0);
  }
}
.chat-input__send {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  border: none;
  background: #4f46e5;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
  flex-shrink: 0;
}
.chat-input__send:hover:not(:disabled) {
  background: #4338ca;
}
.chat-input__send:disabled {
  background: #c7d2fe;
  cursor: not-allowed;
}
.chat-input__stop {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  border: none;
  background: #ef4444;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
  flex-shrink: 0;
}
.chat-input__stop:hover {
  background: #dc2626;
}
.chat-input__hint {
  text-align: right;
  padding-top: 4px;
  padding-right: 4px;
}
.chat-input__remaining {
  font-size: 12px;
  color: #9ca3af;
}
.chat-input__remaining--exhausted {
  color: #ef4444;
  font-weight: 500;
}
</style>
