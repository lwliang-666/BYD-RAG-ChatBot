/**
 * composables/use-typewriter.js - 流式文本打字机
 *
 * 大模型按 token 下发内容，节奏并不均匀（可能一次几十个字符，也可能停顿数秒），
 * 直接赋值渲染会出现文字成块跳出、闪烁跳行的问题。
 *
 * 这里把收到的文本放进缓冲区，由 requestAnimationFrame 按帧均匀释放：
 * 平时以基础速度输出，积压较多时自动加速追赶，流结束后加速收尾，
 * 让输出节奏接近 DeepSeek 等对话产品的逐字效果。
 */
import { ref, onUnmounted } from 'vue'

// 基础输出速度（字符/秒）
const BASE_CPS = 40
// 追赶系数：每积压 1 个字符，输出速度额外增加该值（字符/秒）
const CATCH_UP = 2.5
// 最大输出速度（字符/秒）
const MAX_CPS = 800
// 流结束后剩余内容的加速倍数，用于快速收尾
const FINISH_BOOST = 3
// 单帧最大时间步长（毫秒），避免页面切回前台时瞬间吐出一大段
const MAX_FRAME_MS = 100
// 首个数据块超过该长度时直接展示（如断线重连时后端重放已保存的完整回答）
const INSTANT_THRESHOLD = 240

export function useTypewriter() {
  // 当前已呈现的文本
  const displayedText = ref('')

  // 待输出的字符队列（按码点存放，兼容 emoji 等代理对字符）
  let queue = []
  // requestAnimationFrame 句柄
  let frameId = null
  // 上一帧时间戳
  let lastTime = 0
  // 不足一个字符的输出量累积值
  let carry = 0
  // 数据流是否已结束
  let finished = false
  // 等待队列排空的回调
  let drainResolvers = []

  /** 唤醒所有等待排空的回调 */
  function resolveDrain() {
    if (!drainResolvers.length) return
    const resolvers = drainResolvers
    drainResolvers = []
    resolvers.forEach((resolve) => resolve())
  }

  /** 启动渲染循环 */
  function startLoop() {
    if (frameId !== null) return
    lastTime = performance.now()
    frameId = requestAnimationFrame(tick)
  }

  /** 每帧从队列中释放一定数量的字符 */
  function tick(now) {
    frameId = null
    const dt = Math.min(now - lastTime, MAX_FRAME_MS)
    lastTime = now

    if (queue.length > 0) {
      // 积压越多输出越快，保证长时间不会落后于模型
      let cps = Math.min(BASE_CPS + queue.length * CATCH_UP, MAX_CPS)
      if (finished) cps *= FINISH_BOOST
      carry += (cps * dt) / 1000

      const count = Math.min(Math.floor(carry), queue.length)
      if (count > 0) {
        carry -= count
        displayedText.value += queue.splice(0, count).join('')
      }
    }

    if (queue.length > 0) {
      startLoop()
    } else {
      resolveDrain()
    }
  }

  /**
   * 追加新接收到的文本
   * @param {string} text - 本次收到的增量内容
   */
  function push(text) {
    if (!text) return

    // 首个数据块极长时不做动画，直接完整展示
    if (!displayedText.value && !queue.length && text.length > INSTANT_THRESHOLD) {
      displayedText.value = text
      return
    }

    for (const ch of text) queue.push(ch)
    startLoop()
  }

  /** 标记数据流结束，剩余内容加速输出 */
  function finish() {
    finished = true
    if (queue.length === 0) resolveDrain()
    else startLoop()
  }

  /** 立即输出缓冲区中的全部剩余内容（用户中断时使用） */
  function flush() {
    if (frameId !== null) {
      cancelAnimationFrame(frameId)
      frameId = null
    }
    if (queue.length > 0) {
      displayedText.value += queue.join('')
      queue = []
    }
    carry = 0
    finished = true
    resolveDrain()
  }

  /** 清空并复位，用于开始新一轮回答 */
  function reset() {
    if (frameId !== null) {
      cancelAnimationFrame(frameId)
      frameId = null
    }
    queue = []
    carry = 0
    finished = false
    displayedText.value = ''
    resolveDrain()
  }

  /**
   * 等待缓冲区排空
   * @returns {Promise<void>} 队列为空时 resolve
   */
  function waitDrained() {
    if (queue.length === 0) return Promise.resolve()
    return new Promise((resolve) => drainResolvers.push(resolve))
  }

  // 组件卸载时停止渲染循环，避免回调访问已卸载组件的响应式数据
  onUnmounted(reset)

  return { displayedText, push, finish, flush, reset, waitDrained }
}
