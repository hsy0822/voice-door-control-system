<template>
  <div class="page-safe">
    <van-nav-bar title="出入日志" left-arrow @click-left="$router.back()" />

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-list
        v-model:loading="loading"
        :finished="finished"
        finished-text="没有更多了"
        @load="onLoad"
      >
        <van-empty v-if="!records.length && finished && !loading" description="暂无出入记录" />

        <van-cell-group v-for="row in records" :key="row.id || row.time" inset class="card">
          <van-cell :title="row.time || row.createdAt" :label="row.place || row.location || ''">
            <template #value>
              <div class="cell-right">
                <van-tag :type="row.success !== false ? 'success' : 'danger'">
                  {{ row.success !== false ? '成功' : '失败' }}
                </van-tag>
                <div class="sub">
                  <span>{{ row.mode === 'visitor' ? '访客' : '本人' }}</span>
                  <span v-if="row.abnormal" class="bad">异常</span>
                </div>
              </div>
            </template>
          </van-cell>
        </van-cell-group>
      </van-list>
    </van-pull-refresh>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { showToast } from 'vant'
import { useAuthStore } from '@/stores/auth'
import { fetchUserLogsApi } from '@/api/index'
import { toastApiError } from '@/api/http'

const auth = useAuthStore()

const records = ref([])
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const page = ref(1)

async function fetchPage(reset) {
  if (reset) {
    page.value = 1
    finished.value = false
    records.value = []
  }
  loading.value = true
  try {
    const data = await fetchUserLogsApi({ userId: auth.userId, page: page.value, pageSize: 15 })
    const rows = data.list || data.rows || data.data?.list || []
    if (reset) records.value = rows
    else records.value = records.value.concat(rows)
    if (!rows.length || rows.length < 15) finished.value = true
    else page.value++
  } catch (e) {
    toastApiError(e, '加载日志失败')
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
</script>

<style scoped>
.card {
  margin-top: 10px;
}
.cell-right {
  text-align: right;
  font-size: 12px;
}
.sub {
  margin-top: 6px;
  color: #969799;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.bad {
  color: #ee0a24;
  font-weight: 600;
}
</style>
