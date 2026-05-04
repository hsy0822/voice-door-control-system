import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const STORAGE_USER = 'vd_user'
const STORAGE_TOKEN = 'vd_token'

function loadUser() {
  try {
    const raw = localStorage.getItem(STORAGE_USER)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref(loadUser())
  const token = ref(localStorage.getItem(STORAGE_TOKEN) || '')

  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const role = computed(() => user.value?.role || '')
  const userId = computed(() => user.value?.id ?? user.value?.userId ?? '')

  function setSession({ accessToken, profile }) {
    token.value = accessToken || ''
    user.value = profile || null
    if (accessToken) localStorage.setItem(STORAGE_TOKEN, accessToken)
    else localStorage.removeItem(STORAGE_TOKEN)
    if (profile) localStorage.setItem(STORAGE_USER, JSON.stringify(profile))
    else localStorage.removeItem(STORAGE_USER)
  }

  function logout() {
    setSession({ accessToken: '', profile: null })
  }

  return { user, token, isLoggedIn, role, userId, setSession, logout }
})
