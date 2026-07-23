<!--
  App.vue - 应用根组件
  作为整个应用的入口容器，提供路由视图挂载点和全局样式重置
-->
<template>
  <router-view />
  <!-- 全局 toast 通知容器 -->
  <div id="toast-container"></div>
</template>

<style>
/* 全局样式重置：消除浏览器默认间距，统一盒模型 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

/* 全局字体设置：使用系统字体栈，开启字体平滑渲染 */
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 自定义滚动条样式：窄轨道 + 圆角滑块 */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

/* toast 通知样式 */
#toast-container {
  position: fixed;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  pointer-events: none;
}
.toast {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  color: #fff;
  background: #1f2937;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  animation: toast-in 0.25s ease-out;
  pointer-events: auto;
}
.toast--success {
  background: #059669;
}
.toast--error {
  background: #dc2626;
}
.toast--leaving {
  animation: toast-out 0.2s ease-in forwards;
}
@keyframes toast-in {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes toast-out {
  from { opacity: 1; transform: translateY(0); }
  to { opacity: 0; transform: translateY(-8px); }
}
</style>
