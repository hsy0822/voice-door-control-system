<template>
  <div class="page-safe">
    <van-nav-bar title="异常告警" left-arrow @click-left="$router.push('/admin')" />

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-list v-model:loading="loading" :finished="finished" finished-text="没有更多了" @load="onLoad">
        <van-empty v-if="!items.length && finished && !loading" description="暂无告警" />

        <van-cell-group v-for="row in items" :key="row.id" inset class="card">
          <van-cell :title="row.userName || row.user || '未知用户'" :label="row.place || row.location">
            <template #value>
              <div class="right">
                <van-tag :type="emotionType(row.emotion)">{{ emotionText(row.emotion) }}</van-tag>
                <div class="time">{{ row.time || row.createdAt }}</div>
              </div>
            </template>
          </van-cell>
          <div class="actions">
            <van-button size="small" plain type="primary" @click="showDetail(row)">详情</van-button>
            <van-button
              size="small"
              type="success"
              plain
              :disabled="row.resolved"
              @click="markDone(row)"
            >
              {{ row.resolved ? '已处理' : '标记已处理' }}
            </van-button>
          </div>
        </van-cell-group>
      </van-list>
    </van-pull-refresh>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { showToast, showDialog } from 'vant'
import { fetchAlarmsApi, resolveAlarmApi } from '@/api/index'
import { toastApiError } from '@/api/http'

const items = ref([])
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const page = ref(1)

function emotionText(e) {
  const m = { fear: '恐惧', nervous: '紧张', tension: '紧张', coercion: '胁迫' }
  return m[e] || e || '异常'
}

function emotionType(e) {
  if (e === 'fear') return 'danger'
  return 'warning'
}

async function fetchPage(reset) {
  if (reset) {
    page.value = 1
    finished.value = false
    items.value = []
  }
  loading.value = true
  try {
    const data = await fetchAlarmsApi({ page: page.value, pageSize: 15 })
    const rows = data.list || data.rows || data.data?.list || []
    if (reset) items.value = rows
    else items.value = items.value.concat(rows)
    if (!rows.length || rows.length < 15) finished.value = true
    else page.value++
  } catch (e) {
    toastApiError(e, '加载告警失败')
    finished.value = true
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

function onLoad() {
  if (refreshing.value) return
  fetchPage(false)
}

function onRefresh() {
  refreshing.value = true
  fetchPage(true).then(() => showToast('已刷新'))
}

function showDetail(row) {
  showDialog({
    title: '告警详情',
    message: [
      `用户：${row.userName || row.user || '—'}`,
      `时间：${row.time || row.createdAt || '—'}`,
      `地点：${row.place || row.location || '—'}`,
      `情绪：${emotionText(row.emotion)}`,
      row.detail || row.description || '',
    ]
      .filter(Boolean)
      .join('\n'),
  })
}

async function markDone(row) {
  try {
    await resolveAlarmApi(row.id)
    row.resolved = true
    showToast('已标记处理')
  } catch (e) {
    toastApiError(e, '操作失败')
  }
}
</script>

<style scoped>
.card {
  margin-top: 10px;
}
.right {
  text-align: right;
}
.time {
  margin-top: 6px;
  font-size: 12px;
  color: #969799;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 0 16px 12px;
  background: #fff;
}
</style>
