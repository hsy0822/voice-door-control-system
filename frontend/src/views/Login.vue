<template>
  <div class="page-safe login-page">
    <div class="hero">
      <h1 class="title">{{ title }}</h1>
      <p class="sub">安全 · 动态口令 · 声纹核验</p>
    </div>

    <van-cell-group inset class="form-card">
      <van-field v-model="username" label="用户名" placeholder="请输入用户名" clearable />
      <van-field
        v-model="password"
        type="password"
        label="密码"
        placeholder="请输入密码"
        clearable
      />
    </van-cell-group>

    <div class="role-row">
      <span class="role-label">角色</span>
      <van-button
        :type="role === 'resident' ? 'primary' : 'default'"
        size="small"
        round
        @click="role = 'resident'"
      >
        住户
      </van-button>
      <van-button
        :type="role === 'admin' ? 'primary' : 'default'"
        size="small"
        round
        @click="role = 'admin'"
      >
        管理员
      </van-button>
    </div>

    <div class="actions">
      <van-button type="primary" block round :loading="loading" @click="onLogin">登录</van-button>
      <van-button
        v-if="role === 'resident'"
        block
        round
        plain
        hairline
        type="primary"
        class="mt"
        @click="$router.push('/register')"
      >
        注册新住户
      </van-button>
    </div>

    <footer class="footer">© {{ year }} 动态声纹智能门禁</footer>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast } from 'vant'
import { useAuthStore } from '@/stores/auth'
import { loginApi } from '@/api/index'
import { toastApiError } from '@/api/http'

const title = '动态声纹智能门禁'
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const role = ref('resident')
const loading = ref(false)
const year = computed(() => new Date().getFullYear())

async function onLogin() {
  if (!username.value.trim() || !password.value) {
    showToast('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const data = await loginApi({
      username: username.value.trim(),
      password: password.value,
      role: role.value,
    })
    const token = data.token || data.accessToken || data.data?.token
    const profile = data.user ||
      data.profile || {
        id: data.userId ?? username.value,
        username: username.value,
        role: data.role ?? role.value,
      }
    if (!token) {
      showToast('登录响应缺少令牌，请检查后端')
      return
    }
    auth.setSession({
      accessToken: token,
      profile: { ...profile, role: profile.role || role.value },
    })
    showToast({ type: 'success', message: '登录成功' })
    const redirect = route.query.redirect
    if (redirect && typeof redirect === 'string') {
      router.replace(redirect)
      return
    }
    router.replace(role.value === 'admin' ? '/admin' : '/user-center')
  } catch (e) {
    toastApiError(e, '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  padding: 24px 16px;
}
.hero {
  text-align: center;
  margin-bottom: 28px;
}
.title {
  margin: 0;
  font-size: 22px;
  color: #323233;
}
.sub {
  margin: 8px 0 0;
  color: #969799;
  font-size: 13px;
}
.form-card {
  margin-bottom: 16px;
}
.role-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px 16px;
}
.role-label {
  color: #646566;
  font-size: 14px;
  margin-right: 4px;
}
.actions {
  padding: 0 16px;
}
.mt {
  margin-top: 12px;
}
.footer {
  margin-top: 48px;
  text-align: center;
  color: #c8c9cc;
  font-size: 12px;
}
</style>
