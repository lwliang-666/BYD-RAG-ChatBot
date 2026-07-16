<!--
  App.vue - 应用根组件
  作为整个应用的入口容器，提供路由视图挂载点和全局样式重置
-->
<template>
  <!-- 路由视图：根据当前路由渲染对应的页面组件 -->
  <router-view />
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
</style>
