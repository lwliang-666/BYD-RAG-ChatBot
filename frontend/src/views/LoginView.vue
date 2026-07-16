<!--
  LoginView.vue - 登录页面
  提供用户名/密码登录表单，支持密码显示切换和错误提示
-->
<template>
  <div class="auth-page">
    <!-- 品牌区域：产品名称和副标题 -->
    <div class="brand">
      <h1 class="brand__title">比亚迪驱逐舰05</h1>
      <div class="brand__divider"></div>
      <p class="brand__subtitle">智能问答助手</p>
    </div>
    <!-- 登录表单卡片 -->
    <div class="auth-card">
      <h2 class="auth-card__title">登录</h2>
      <form class="auth-card__form" @submit.prevent="handleLogin">
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
              <!-- 眼睛打开：显示密码 -->
              <svg v-if="showPassword" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <!-- 眼睛关闭：隐藏密码 -->
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
        <!-- 登录按钮 -->
        <button type="submit" class="auth-card__btn" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
      <!-- 跳转注册链接 -->
      <p class="auth-card__link">
        还没有账号？<router-link to="/register">立即注册</router-link>
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
const error = ref('')
const loading = ref(false)
const showPassword = ref(false)

/** 处理登录表单提交 */
async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await authStore.login(username.value, password.value)
    // 登录成功，跳转到聊天主页
    router.push('/')
  } catch (e) {
    error.value = '用户名或密码错误'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 引入 Google Fonts 中文艺术字体：ZCOOL XiaoWei 优雅衬线 */
@import url('https://fonts.googleapis.com/css2?family=ZCOOL+XiaoWei&family=Noto+Serif+SC:wght@700;900&display=swap');

.auth-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
}
/* 背景装饰光斑，增强层次感 */
.auth-page::before,
.auth-page::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.35;
  pointer-events: none;
}
.auth-page::before {
  width: 480px;
  height: 480px;
  top: -120px;
  left: -120px;
  background: radial-gradient(circle, #a78bfa 0%, transparent 70%);
}
.auth-page::after {
  width: 520px;
  height: 520px;
  bottom: -160px;
  right: -160px;
  background: radial-gradient(circle, #60a5fa 0%, transparent 70%);
}
.brand {
  position: relative;
  z-index: 1;
  text-align: center;
  margin-bottom: 40px;
  user-select: none;
}
.brand__title {
  font-family: 'ZCOOL XiaoWei', 'Noto Serif SC', 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 52px;
  font-weight: 400;
  letter-spacing: 8px;
  margin: 0;
  background: linear-gradient(135deg, #ffffff 0%, #e0e7ff 40%, #c4b5fd 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 4px 20px rgba(255, 255, 255, 0.15);
  filter: drop-shadow(0 6px 24px rgba(124, 58, 237, 0.45));
}
/* 品牌分隔线：渐变线条 + 中心光点 */
.brand__divider {
  width: 160px;
  height: 2px;
  margin: 18px auto;
  background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.7) 50%, transparent 100%);
  position: relative;
}
.brand__divider::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ffffff;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 12px rgba(255, 255, 255, 0.9);
}
.brand__subtitle {
  font-family: 'Noto Serif SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 14px;
  padding-left: 14px; /* 视觉居中补偿字间距 */
  margin: 0;
  color: rgba(255, 255, 255, 0.92);
  text-shadow: 0 2px 12px rgba(76, 29, 149, 0.5);
}
.auth-card {
  position: relative;
  z-index: 1;
  background: #fff;
  border-radius: 16px;
  padding: 40px;
  width: 400px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
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
