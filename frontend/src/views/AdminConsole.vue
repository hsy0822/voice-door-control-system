<template>
  <div class="page-safe admin">
    <van-nav-bar title="管理员控制台" />

    <div class="stats">
      <div class="stat-card">
        <div class="num">{{ stats.totalOpens ?? '—' }}</div>
        <div class="lab">总开门次数</div>
      </div>
      <div class="stat-card warn">
        <div class="num">{{ stats.alarmCount ?? '—' }}</div>
        <div class="lab">异常告警次数</div>
      </div>
    </div>

    <van-cell-group inset title="管理菜单">
      <van-cell title="全部门禁日志" is-link to="/admin/door-logs" icon="records" />
      <van-cell title="异常胁迫告警" is-link to="/admin/alarms" icon="warning-o" />
      <van-cell title="住户权限管理" is-link to="/admin/residents" icon="friends-o" />
    </van-cell-group>

    <div class="logout-wrap">
      <van-button block round type="danger" plain hairline @click="onLogout">退出登录</van-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { showConfirmDialog, showToast } from 'vant'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { fetchAdminStatsApi } from '@/api/index'
import { toastApiError } from '@/api/http'

const auth = useAuthStore()
const router = useRouter()

const stats = ref({ totalOpens: null, alarmCount: null })

async function loadStats() {
  try {
    const data = await fetchAdminStatsApi()
    stats.value = {
      totalOpens: data.totalOpens ?? data.openCount ?? data.total,
      alarmCount: data.alarmCount ?? data.abnormalCount ?? data.alarms,
    }
  } catch (e) {
    toastApiError(e, '统计数据加载失败')
  }
}

function onLogout() {
  showConfirmDialog({ title: '退出登录', message: '确定退出管理员账号？' })
    .then(() => {
      auth.logout()
      showToast('已退出')
      router.replace('/login')
    })
    .catch(() => {})
}

onMounted(loadStats)
</script>

<style scoped>
.admin {
  padding-bottom: 24px;
}
.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 16px;
}
.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 18px;
  text-align: center;
  box-shadow: 0 2px 10px rgba(25, 137, 250, 0.12);
  border: 1px solid #e1efff;
}
.stat-card.warn {
  border-color: #ffe2e0;
  box-shadow: 0 2px 10px rgba(238, 10, 36, 0.08);
}
.num {
  font-size: 26px;
  font-weight: 700;
  color: #1989fa;
}
.warn .num {
  color: #ee0a24;
}
.lab {
  margin-top: 6px;
  font-size: 13px;
  color: #969799;
}
.logout-wrap {
  padding: 28px 16px;
}
</style>
