<template>
  <div class="avatar-upload" @click="triggerUpload">
    <img
      v-if="modelValue"
      :src="modelValue"
      alt="avatar"
      class="avatar-upload__img"
    />
    <img
      v-else
      src="../assets/default-avatar.svg"
      alt="avatar"
      class="avatar-upload__img"
    />
    <div class="avatar-upload__overlay">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2">
        <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
        <circle cx="12" cy="13" r="4"/>
      </svg>
    </div>
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

const props = defineProps({
  modelValue: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'upload'])

const inputRef = ref(null)

function triggerUpload() {
  inputRef.value?.click()
}

function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  emit('upload', file)
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
.avatar-upload:hover .avatar-upload__overlay {
  opacity: 1;
}
.avatar-upload__input {
  display: none;
}
</style>
