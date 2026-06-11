<template>
  <div class="page-safe uc">
    <van-nav-bar title="个人中心" />

    <div class="profile">
      <div class="avatar">{{ (auth.user?.username || '?').slice(0, 1) }}</div>
      <div class="meta">
        <div class="name">{{ auth.user?.username }}</div>
        <van-tag type="primary" plain>住户</van-tag>
      </div>
    </div>

    <van-cell-group inset>
      <van-cell title="开门鉴权" is-link to="/open-door" icon="shield-o" />
      <van-cell title="声纹管理（录入 / 重置）" is-link to="/voice-print" icon="music-o" />
      <van-cell title="访客临时授权" is-link to="/visitor-auth" icon="friends-o" />
      <van-cell title="我的出入日志" is-link to="/user-log" icon="records" />
    </van-cell-group>

    <div class="logout-wrap">
      <van-button block round type="danger" plain hairline @click="onLogout">退出登录</van-button>
    </div>
  </div>
</template>

<script setup>
import { showConfirmDialog, showToast } from 'vant'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

function onLogout() {
  showConfirmDialog({
    title: '退出登录',
    message: '确定退出当前账号？',
  })
    .then(() => {
      auth.logout()
      showToast('已退出')
      router.replace('/login')
    })
    .catch(() => {})
}
</script>

<style scoped>
.uc {
  padding-bottom: 24px;
}
.profile {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 16px;
  background: linear-gradient(180deg, #e8f4ff 0%, #f7f8fa 100%);
}
.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #1989fa;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  font-weight: 700;
}
.meta .name {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 6px;
}
.logout-wrap {
  padding: 24px 16px;
}
</style>
