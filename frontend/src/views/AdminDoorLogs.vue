<template>
  <div class="page-safe">
    <van-nav-bar title="全部门禁日志" left-arrow @click-left="$router.push('/admin')" />

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-list v-model:loading="loading" :finished="finished" finished-text="没有更多了" @load="onLoad">
        <van-empty v-if="!rows.length && finished && !loading" description="暂无日志" />

        <van-cell-group v-for="(row, idx) in rows" :key="row.id || idx" inset class="card">
          <van-cell :title="row.time || row.createdAt" :label="row.userName || row.user || ''">
            <template #value>
              <div class="val">
                <van-tag :type="row.abnormal ? 'danger' : 'primary'" plain>
                  {{ row.abnormal ? '异常' : '正常' }}
                </van-tag>
                <div class="sub">{{ row.result || (row.success !== false ? '成功' : '失败') }}</div>
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
import { fetchAdminDoorLogsApi } from '@/api/index'
import { toastApiError } from '@/api/http'

const rows = ref([])
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const page = ref(1)

async function fetchPage(reset) {
  if (reset) {
    page.value = 1
    finished.value = false
    rows.value = []
  }
  loading.value = true
  try {
    const data = await fetchAdminDoorLogsApi({ page: page.value, pageSize: 20 })
    const list = data.list || data.rows || data.data?.list || []
    if (reset) rows.value = list
    else rows.value = rows.value.concat(list)
    if (!list.length || list.length < 20) finished.value = true
    else page.value++
  } catch (e) {
    toastApiError(e, '加载失败')
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
.val {
  text-align: right;
}
.sub {
  margin-top: 6px;
  font-size: 12px;
  color: #969799;
}
</style>
