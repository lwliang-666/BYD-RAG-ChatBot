/**
 * api-error.js - 请求异常提示转换
 * 将 axios 异常转换为用户可读的提示文案，区分业务错误与网络层错误
 */

/**
 * 根据请求异常生成提示文案
 * @param {Error} error axios 抛出的异常对象
 * @param {object} options 可选配置
 * @param {string} options.unauthorized 401 时使用的提示文案
 * @param {string} options.fallback 无法识别错误时使用的兜底文案
 * @returns {string} 用户可读的错误提示
 */
export function getApiErrorMessage(error, options = {}) {
  const {
    unauthorized = '登录状态已失效，请重新登录',
    fallback = '操作失败，请稍后重试',
  } = options

  // 没有 response 说明请求未到达后端：断网、DNS 失败、TLS 证书错误或超时
  if (!error?.response) {
    if (error?.code === 'ECONNABORTED' || error?.code === 'ETIMEDOUT') {
      return '请求超时，请稍后重试'
    }
    return '无法连接服务器，请检查网络后重试'
  }

  const { status, data } = error.response

  if (status === 401) {
    return unauthorized
  }
  if (status === 403) {
    return '没有权限执行该操作'
  }
  if (status >= 500) {
    return '服务暂时不可用，请稍后重试'
  }

  // 后端返回的业务错误优先展示
  if (typeof data?.detail === 'string' && data.detail) {
    return data.detail
  }
  return fallback
}
