<template>
  <div class="page-safe">
    <van-nav-bar title="住户权限管理" left-arrow @click-left="$router.push('/admin')" />

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-list v-model:loading="loading" :finished="finished" finished-text="没有更多了" @load="onLoad">
        <van-empty v-if="!residents.length && finished && !loading" description="暂无住户数据" />

        <van-cell-group v-for="r in residents" :key="r.id" inset class="card">
          <van-cell :title="r.username || r.name" :label="`门禁：${r.doorAuth !== false ? '已授权' : '停用'}`">
            <template #value>
              <van-switch
                :model-value="r.doorAuth !== false"
                size="20px"
                @update:model-value="(v) => toggle(r, v)"
              />
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
import { fetchResidentsApi } from '@/api/index'
import { toastApiError } from '@/api/http'

const residents = ref([])
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const page = ref(1)

async function fetchPage(reset) {
  if (reset) {
    page.value = 1
    finished.value = false
    residents.value = []
  }
  loading.value = true
  try {
    const data = await fetchResidentsApi({ page: page.value, pageSize: 20 })
    const list = data.list || data.rows || data.data?.list || []
    if (reset) residents.value = list
    else residents.value = residents.value.concat(list)
    if (!list.length || list.length < 20) finished.value = true
    else page.value++
  } catch (e) {
    toastApiError(e, '加载住户失败')
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

function toggle(row, enabled) {
  row.doorAuth = enabled
  showToast(enabled ? '已授权（请对接后端持久化）' : '已停用（本地演示）')
}
</script>

<style scoped>
.card {
  margin-top: 10px;
}
</style>
