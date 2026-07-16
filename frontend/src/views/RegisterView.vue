<!--
  RegisterView.vue - 注册页面
  提供用户名/密码/确认密码注册表单，支持密码显示切换和错误提示
-->
<template>
  <div class="auth-page">
    <!-- 注册表单卡片 -->
    <div class="auth-card">
      <h2 class="auth-card__title">注册</h2>
      <form class="auth-card__form" @submit.prevent="handleRegister">
        <!-- 用户名输入 -->
        <div class="auth-card__field">
          <label>用户名</label>
          <input v-model="username" type="text" required minlength="3" maxlength="50" placeholder="请输入用户名" />
        </div>
        <!-- 密码输入（含显示/隐藏切换） -->
        <div class="auth-card__field">
          <label>密码</label>
          <div class="auth-card__input-wrapper">
            <input v-model="password" :type="showPassword ? 'text' : 'password'" required minlength="6" maxlength="72" placeholder="请输入密码" />
            <!-- 密码可见性切换按钮 -->
            <button type="button" class="auth-card__toggle-pwd" @click="showPassword = !showPassword" :aria-label="showPassword ? '隐藏密码' : '显示密码'">
              <svg v-if="showPassword" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
                <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/>
              </svg>
            </button>
          </div>
        </div>
        <!-- 确认密码输入（含显示/隐藏切换） -->
        <div class="auth-card__field">
          <label>确认密码</label>
          <div class="auth-card__input-wrapper">
            <input v-model="confirmPassword" :type="showConfirmPassword ? 'text' : 'password'" required minlength="6" maxlength="72" placeholder="请再次输入密码" />
            <button type="button" class="auth-card__toggle-pwd" @click="showConfirmPassword = !showConfirmPassword" :aria-label="showConfirmPassword ? '隐藏密码' : '显示密码'">
              <svg v-if="showConfirmPassword" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
                <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/>
              </svg>
            </button>
          </div>
        </div>
        <!-- 错误提示 -->
        <p v-if="error" class="auth-card__error">{{ error }}</p>
        <!-- 注册按钮 -->
        <button type="submit" class="auth-card__btn" :disabled="loading">
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>
      <!-- 跳转登录链接 -->
      <p class="auth-card__link">
        已有账号？<router-link to="/login">立即登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// 表单数据
const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)
const showPassword = ref(false)
const showConfirmPassword = ref(false)

/** 处理注册表单提交 */
async function handleRegister() {
  error.value = ''
  // 前端校验：两次密码是否一致
  if (password.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  try {
    await authStore.register(username.value, password.value)
    // 注册成功，跳转到聊天主页
    router.push('/')
  } catch (e) {
    // 优先显示后端返回的错误信息
    const detail = e.response?.data?.detail
    error.value = detail || '注册失败，请稍后再试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.auth-card {
  background: #fff;
  border-radius: 16px;
  padding: 40px;
  width: 400px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}
.auth-card__title {
  text-align: center;
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 32px;
}
.auth-card__field {
  margin-bottom: 20px;
}
.auth-card__field label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 6px;
}
.auth-card__field input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.auth-card__field input:focus {
  border-color: #4f46e5;
}
.auth-card__input-wrapper {
  position: relative;
}
.auth-card__input-wrapper input {
  width: 100%;
  padding: 10px 40px 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.auth-card__input-wrapper input:focus {
  border-color: #4f46e5;
}
/* 密码可见性切换按钮 */
.auth-card__toggle-pwd {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 0;
}
.auth-card__toggle-pwd:hover {
  color: #4f46e5;
}
.auth-card__error {
  color: #ef4444;
  font-size: 13px;
  margin-bottom: 12px;
}
.auth-card__btn {
  width: 100%;
  padding: 12px;
  background: #4f46e5;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}
.auth-card__btn:hover:not(:disabled) {
  background: #4338ca;
}
.auth-card__btn:disabled {
  background: #c7d2fe;
  cursor: not-allowed;
}
.auth-card__link {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
  color: #6b7280;
}
.auth-card__link a {
  color: #4f46e5;
  text-decoration: none;
  font-weight: 500;
}
</style>
