/**
 * router/index.js - 前端路由配置
 * 定义应用的路由规则和导航守卫，控制页面访问权限
 */
import { createRouter, createWebHistory } from 'vue-router'

// 路由配置：使用懒加载方式引入页面组件
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/LoginView.vue'),
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('../views/RegisterView.vue'),
    },
    {
      path: '/',
      name: 'Chat',
      component: () => import('../views/ChatView.vue'),
      meta: { requiresAuth: true },  // 标记需要登录才能访问
    },
  ],
})

/**
 * 全局前置导航守卫
 * - 需要认证的页面：未登录时重定向到登录页
 * - 登录/注册页面：已登录时重定向到聊天页
 */
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  if (to.meta.requiresAuth && !token) {
    // 未登录访问需认证页面 -> 跳转登录
    next({ name: 'Login' })
  } else if ((to.name === 'Login' || to.name === 'Register') && token) {
    // 已登录访问登录/注册页 -> 跳转聊天
    next({ name: 'Chat' })
  } else {
    next()
  }
})

export default router
