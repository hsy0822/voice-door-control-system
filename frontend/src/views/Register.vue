<template>
  <div class="page-safe">
    <van-nav-bar title="住户注册" left-arrow @click-left="$router.back()" />

    <van-cell-group inset class="card">
      <van-field v-model="username" label="用户名" placeholder="设置用户名" clearable />
      <van-field v-model="password" type="password" label="密码" placeholder="设置密码" clearable />
      <van-field
        v-model="password2"
        type="password"
        label="确认密码"
        placeholder="再次输入密码"
        clearable
      />
    </van-cell-group>

    <div class="pad">
      <van-button type="primary" block round :loading="loading" @click="submit">注册</van-button>
      <van-button block round plain hairline type="primary" class="mt" @click="$router.push('/login')">
        返回登录
      </van-button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { registerApi } from '@/api/index'
import { toastApiError } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const password2 = ref('')
const loading = ref(false)

async function submit() {
  if (!username.value.trim()) {
    showToast('请输入用户名')
    return
  }
  if (password.value.length < 6) {
    showToast('密码至少 6 位')
    return
  }
  if (password.value !== password2.value) {
    showToast('两次密码不一致')
    return
  }
  loading.value = true
  try {
    const data = await registerApi({
      username: username.value.trim(),
      password: password.value,
    })
    const token = data.token || data.accessToken
    const profile = data.user || {
      id: data.userId ?? username.value,
      username: username.value,
      role: 'resident',
    }
    if (token) {
      auth.setSession({ accessToken: token, profile: { ...profile, role: 'resident' } })
    }
    showToast({ type: 'success', message: '注册成功，请录入声纹' })
    router.replace('/voice-print')
  } catch (e) {
    toastApiError(e, '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.card {
  margin-top: 12px;
}
.pad {
  padding: 20px 16px;
}
.mt {
  margin-top: 12px;
}
</style>
