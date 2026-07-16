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
