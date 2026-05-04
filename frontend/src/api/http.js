import axios from 'axios'
import { showLoadingToast, closeToast, showFailToast } from 'vant'

const baseURL = import.meta.env.VITE_API_BASE || '/api'

export const http = axios.create({
  baseURL,
  timeout: 60000,
})

let loadingCount = 0

function loadingOpen() {
  if (loadingCount === 0) {
    showLoadingToast({
      message: '加载中…',
      forbidClick: true,
      duration: 0,
    })
  }
  loadingCount++
}

function loadingClose() {
  loadingCount = Math.max(0, loadingCount - 1)
  if (loadingCount === 0) closeToast()
}

http.interceptors.request.use(
  (config) => {
    const skip = config.skipLoading === true
    if (!skip) loadingOpen()
    const token = localStorage.getItem('vd_token')
    if (token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (err) => {
    loadingClose()
    return Promise.reject(err)
  },
)

http.interceptors.response.use(
  (res) => {
    loadingClose()
    return res
  },
  (err) => {
    loadingClose()
    const msg = err.response?.data?.message || err.message || '网络异常'
    if (err.response?.status === 401) {
      localStorage.removeItem('vd_token')
      localStorage.removeItem('vd_user')
      if (!window.location.hash.startsWith('#/login')) {
        window.location.hash = '#/login'
      }
    }
    return Promise.reject(err)
  },
)

export function toastApiError(err, fallback = '请求失败') {
  const msg = err.response?.data?.message || err.message || fallback
  showFailToast(msg)
}
