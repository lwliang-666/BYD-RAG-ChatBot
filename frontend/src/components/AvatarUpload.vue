<!--
  AvatarUpload.vue - 头像上传组件
  点击头像区域触发文件选择，支持图片预览和上传事件回调
  通过 v-model 双向绑定头像 URL，通过 @upload 事件通知父组件处理文件上传
-->
<template>
  <!-- 头像容器：点击触发文件选择 -->
  <div class="avatar-upload" @click="triggerUpload">
    <!-- 已设置头像时显示用户头像 -->
    <img
      v-if="modelValue"
      :src="modelValue"
      alt="avatar"
      class="avatar-upload__img"
    />
    <!-- 未设置头像时显示默认头像 -->
    <img
      v-else
      src="../assets/default-avatar.svg"
      alt="avatar"
      class="avatar-upload__img"
    />
    <!-- 悬停遮罩层：显示相机图标提示可更换头像 -->
    <div class="avatar-upload__overlay">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2">
        <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
        <circle cx="12" cy="13" r="4"/>
      </svg>
    </div>
    <!-- 隐藏的文件输入框，限制图片格式 -->
    <input
      ref="inputRef"
      type="file"
      accept="image/jpeg,image/png,image/gif,image/webp"
      class="avatar-upload__input"
      @change="handleFileChange"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'

// 组件属性：v-model 绑定的头像 URL
const props = defineProps({
  modelValue: { type: String, default: '' },
})

// 组件事件：更新 v-model 值 / 通知父组件上传文件
const emit = defineEmits(['update:modelValue', 'upload'])

// 文件输入框的 DOM 引用
const inputRef = ref(null)

/** 点击头像区域时，触发隐藏的文件输入框 */
function triggerUpload() {
  inputRef.value?.click()
}

/** 文件选择变更回调：将选中的文件通过 upload 事件传递给父组件 */
function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  emit('upload', file)
  // 清空 input 值，确保同一文件可重复选择
  e.target.value = ''
}
</script>

<style scoped>
.avatar-upload {
  position: relative;
  width: 40px;
  height: 40px;
  cursor: pointer;
  border-radius: 50%;
  overflow: hidden;
}
.avatar-upload__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}
.avatar-upload__overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}
/* 悬停时显示遮罩 */
.avatar-upload:hover .avatar-upload__overlay {
  opacity: 1;
}
.avatar-upload__input {
  display: none;
}
</style>
