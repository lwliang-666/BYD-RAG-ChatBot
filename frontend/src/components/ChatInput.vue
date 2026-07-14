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
    <button
      class="chat-input__send"
      :disabled="disabled || !text.trim()"
      @click="handleSend"
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
      </svg>
    </button>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['send'])

const text = ref('')
const textareaRef = ref(null)

function handleSend() {
  if (!text.value.trim() || props.disabled) return
  emit('send', text.value.trim())
  text.value = ''
  nextTick(autoResize)
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
  display: flex;
  align-items: flex-end;
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
</style>
