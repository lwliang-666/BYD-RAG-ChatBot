/**
 * vite.config.js - Vite 构建配置
 * 配置 Vue 插件和开发服务器代理规则
 * 将 /api 和 /uploads 请求代理到后端服务，解决开发环境跨域问题
 */
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  // 注册 Vue 单文件组件编译插件
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // 将 /api 路径的请求代理到后端 FastAPI 服务
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // 将 /uploads 路径的请求代理到后端，用于访问上传的头像等静态资源
      '/uploads': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
