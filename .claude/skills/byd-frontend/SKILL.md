---
name: byd-frontend
description: BYD-RAG-ChatBot 前端开发规范和模式指导。当用户在前端添加新组件、修改 Vue 组件、调整 Pinia store、处理 API 调用、SSE 流式接收、路由配置等前端相关开发时触发。也适用于 "Vue 组件"、"Pinia store"、"前端功能"、"修改 UI"、"聊天界面" 等场景。提供项目已有的 Vue3 + Pinia + vue-router 模式和代码风格参考。
---

# BYD-RAG-ChatBot 前端开发规范

## 目录结构

```
frontend/src/
  views/        ← 页面组件 (LoginView, RegisterView, ChatView)
  components/   ← 可复用组件 (ChatMessage, ChatInput, AvatarUpload)
  stores/       ← Pinia 状态管理 (auth, chat, user)
  api/          ← API 请求封装 (request, auth, chat, user)
  router/       ← 路由配置
  assets/       ← 静态资源
```

## 组件风格

- 使用 `<script setup>` 语法 (Composition API)
- Scoped CSS，BEM-like 命名：`chat-layout`、`sidebar__header`、`sidebar__item--active`
- 通过 `defineExpose` 暴露方法给父组件（如 `ChatInput.setText()`）
- 中文 JSDoc 风格注释

## Pinia Store 模式

使用 Composition API 风格：

```javascript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getXxx } from '../api/xxx'

export const useXxxStore = defineStore('xxx', () => {
  // 状态
  const items = ref([])

  // 异步操作
  async function fetchItems() {
    const res = await getXxx()
    items.value = res.data
  }

  return { items, fetchItems }
})
```

## API 层

`request.js` 封装了 axios 实例，自动附加 JWT Token 和处理 401 刷新：

```javascript
// api/xxx.js
import api from './request'

export function getXxx() {
  return api.get('/api/xxx')
}

export function createXxx(data) {
  return api.post('/api/xxx', data)
}
```

## SSE 流式接收（聊天核心）

使用原生 `fetch()`（axios 不支持 ReadableStream）：

```javascript
const abortController = new AbortController()

const response = await fetch(`/api/chat/conversations/${id}/messages`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  },
  body: JSON.stringify({ content: message }),
  signal: abortController.signal,
})

const reader = response.body.getReader()
const decoder = new TextDecoder()

while (true) {
  const { done, value } = await reader.read()
  if (done) break

  const text = decoder.decode(value)
  // 解析 SSE 格式: "event: token\ndata: {...}\n\n"
  const lines = text.split('\n')
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6))
      // 处理 token / sources / done 事件
    }
  }
}
```

**关键点**：
- 用户中断时调用 `abortController.abort()`
- Markdown 渲染使用 `markdown-it` + `highlight.js`
- 流式内容逐步追加到 `streamingContent` ref

## 路由配置

```javascript
// 需认证的页面添加 meta
{
  path: '/',
  name: 'Chat',
  component: () => import('../views/ChatView.vue'),
  meta: { requiresAuth: true },
}

// 全局守卫自动处理重定向
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  if (to.meta.requiresAuth && !token) {
    next({ name: 'Login' })
  } else { next() }
})
```

## 新增页面流程

1. 在 `views/` 创建组件
2. 在 `router/index.js` 添加路由（懒加载）
3. 如需认证，添加 `meta: { requiresAuth: true }`
4. 在 `api/` 创建对应的 API 模块
5. 在 `stores/` 创建对应的 Pinia store

## Vite 代理配置

`vite.config.js` 已配置代理：
- `/api` → `http://localhost:8000`（后端 API）
- `/uploads` → `http://localhost:8000`（头像等静态文件）

开发时直接使用 `/api/xxx` 路径，无需写完整后端地址。

## 代码风格

- 注释使用中文，JSDoc 风格
- 变量函数：camelCase
- CSS 类名：BEM-like (block__element--modifier)
- 包管理：pnpm
- 不使用 emoji
