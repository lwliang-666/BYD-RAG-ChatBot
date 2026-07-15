<template>
  <div class="chat-input">
    <textarea
      ref="textareaRef"
      v-model="text"
      class="chat-input__textarea"
      placeholder="输入您的问题..."
      rows="1"
      :disabled="disabled"
      @keydown.enter.exact.prevent="handleSend"
      @input="autoResize"
    ></textarea>
    <!-- 发送按钮 -->
    <button
      v-if="!isStreaming"
      class="chat-input__send"
      :disabled="disabled || !text.trim()"
      @click="handleSend"
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
      </svg>
    </button>
    <!-- 停止按钮 -->
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
</template>

<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  isStreaming: { type: Boolean, default: false },
})

const emit = defineEmits(['send', 'stop'])

const text = ref('')
const textareaRef = ref(null)

function handleSend() {
  if (!text.value.trim() || props.disabled) return
  emit('send', text.value.trim())
  text.value = ''
  nextTick(autoResize)
}

function handleStop() {
  emit('stop')
}

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 150) + 'px'
}
</script>

<style scoped>
.chat-input {
    min-height: 75px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
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
</style>
