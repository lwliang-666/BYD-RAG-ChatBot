/**
 * main.js - 应用入口文件
 * 创建 Vue 应用实例，注册 Pinia 状态管理和 Vue Router 路由，挂载到 DOM
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// 创建 Vue 应用实例
const app = createApp(App)

// 注册 Pinia 状态管理插件
app.use(createPinia())

// 注册 Vue Router 路由插件
app.use(router)

// 将应用挂载到 index.html 中的 #app 元素
app.mount('#app')

/**
 * 全局 toast 通知
 * @param {string} message - 提示文本
 * @param {'success'|'error'} type - 提示类型
 * @param {number} duration - 显示时长（毫秒）
 */
window.showToast = function (message, type = 'success', duration = 2000) {
  const container = document.getElementById('toast-container')
  if (!container) return
  const el = document.createElement('div')
  el.className = `toast toast--${type}`
  el.textContent = message
  container.appendChild(el)
  setTimeout(() => {
    el.classList.add('toast--leaving')
    el.addEventListener('animationend', () => el.remove())
  }, duration)
}
