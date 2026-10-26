/**
 * utils/markdown.js - Markdown 渲染工具
 *
 * 统一消息列表与流式输出使用的渲染配置，避免流式阶段与最终消息的
 * 代码高亮、排版样式前后不一致。
 */
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

// 全局共用的 Markdown 渲染器，代码块使用 highlight.js 高亮
const md = new MarkdownIt({
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang }).value
      } catch {}
    }
    return ''
  },
})

// 光标标记：animation-delay 由调用方传入，保证 DOM 重渲染后闪烁节奏连续
function cursorHtml(blinkOffset) {
  return `<span class="stream-cursor" style="animation-delay:-${blinkOffset}ms"></span>`
}

// 需要把光标插入其内部的块级结束标签
const BLOCK_END_TAGS = [
  '</p>', '</li>', '</h1>', '</h2>', '</h3>', '</h4>', '</h5>', '</h6>',
  '</blockquote>', '</pre>', '</td>', '</th>', '</dt>', '</dd>',
]

/**
 * 渲染完整 Markdown 文本
 * @param {string} text - Markdown 原文
 * @returns {string} HTML 字符串
 */
export function renderMarkdown(text) {
  return md.render(text || '')
}

/**
 * 渲染流式 Markdown 文本，并在最后一个块级元素内部追加闪烁光标
 *
 * 光标必须插在最后一个块级标签内部，否则会单独占一行；
 * blinkOffset 用于抵消每帧 innerHTML 重建导致的动画重启。
 *
 * @param {string} text - 当前已呈现的 Markdown 原文
 * @param {number} blinkOffset - 光标动画相位偏移（毫秒）
 * @returns {string} 带光标的 HTML 字符串
 */
export function renderStreamingMarkdown(text, blinkOffset = 0) {
  if (!text) return ''
  const html = md.render(text)

  let insertAt = -1
  for (const tag of BLOCK_END_TAGS) {
    const idx = html.lastIndexOf(tag)
    if (idx > insertAt) insertAt = idx
  }

  const cursor = cursorHtml(blinkOffset)
  if (insertAt === -1) return html + cursor
  return html.slice(0, insertAt) + cursor + html.slice(insertAt)
}
