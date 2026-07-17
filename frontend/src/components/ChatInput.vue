<!--
  ChatInput.vue - 聊天输入框组件
  提供消息输入、发送、停止流式响应、一键清空等功能
  支持自动高度调整、Enter 快捷发送、流式状态切换等交互
-->
<template>
  <div class="chat-input">
    <div class="chat-input__row">
      <!-- 消息输入框：支持自动高度调整和 Enter 快捷发送 -->
      <textarea
        ref="textareaRef"
        v-model="text"
        class="chat-input__textarea"
        placeholder="输入您的问题..."
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
import { ref, nextTick } from 'vue'

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
