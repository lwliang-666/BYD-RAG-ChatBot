<template>
  <div class="auth-page">
    <div class="auth-card">
      <h2 class="auth-card__title">注册</h2>
      <form class="auth-card__form" @submit.prevent="handleRegister">
        <div class="auth-card__field">
          <label>用户名</label>
          <input v-model="username" type="text" required minlength="3" maxlength="50" placeholder="请输入用户名" />
        </div>
        <div class="auth-card__field">
          <label>密码</label>
          <input v-model="password" type="password" required minlength="6" placeholder="请输入密码" />
        </div>
        <div class="auth-card__field">
          <label>确认密码</label>
          <input v-model="confirmPassword" type="password" required minlength="6" placeholder="请再次输入密码" />
        </div>
        <p v-if="error" class="auth-card__error">{{ error }}</p>
        <button type="submit" class="auth-card__btn" :disabled="loading">
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>
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

const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  if (password.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  try {
    await authStore.register(username.value, password.value)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || '注册失败，请稍后再试'
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
