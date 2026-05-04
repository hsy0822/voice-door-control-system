<template>
  <div class="page-safe">
    <van-nav-bar title="访客临时授权" left-arrow @click-left="$router.back()" />

    <van-cell-group inset title="授权类型">
      <van-radio-group v-model="authType">
        <van-cell title="单次有效" clickable @click="authType = 'once'">
          <template #right-icon><van-radio name="once" /></template>
        </van-cell>
        <van-cell title="1 小时有效" clickable @click="authType = 'hour'">
          <template #right-icon><van-radio name="hour" /></template>
        </van-cell>
      </van-radio-group>
    </van-cell-group>

    <div class="pad">
      <van-button type="primary" block round :loading="genLoading" @click="generate">
        生成临时口令
      </van-button>
    </div>

    <van-cell-group v-if="currentToken" inset title="当前口令">
      <van-cell>
        <template #title>
          <span class="token">{{ currentToken }}</span>
        </template>
        <template #right-icon>
          <van-button size="small" type="primary" plain @click="copyToken">复制</van-button>
        </template>
      </van-cell>
    </van-cell-group>

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-cell-group inset title="历史授权">
        <van-empty v-if="!list.length && !listLoading" description="暂无授权记录" />
        <van-swipe-cell v-for="item in list" :key="item.id">
          <van-cell
            :title="item.token || item.code"
            :label="formatItem(item)"
            :value="item.expired ? '已过期' : '有效'"
          />
          <template #right>
            <van-button
              square
              type="danger"
              text="删除"
              class="swipe-btn"
              @click="remove(item)"
            />
          </template>
        </van-swipe-cell>
      </van-cell-group>
    </van-pull-refresh>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { showToast, showSuccessToast } from 'vant'
import { useAuthStore } from '@/stores/auth'
import {
  createVisitorAuthApi,
  listVisitorAuthApi,
  deleteVisitorAuthApi,
} from '@/api/index'
import { toastApiError } from '@/api/http'

const auth = useAuthStore()
const authType = ref('once')
const genLoading = ref(false)
const currentToken = ref('')
const list = ref([])
const listLoading = ref(false)
const refreshing = ref(false)

function formatItem(row) {
  const t = row.createdAt || row.createTime || ''
  const exp = row.expireAt || row.expiresAt || ''
  return [t, exp].filter(Boolean).join(' · ')
}

async function loadList() {
  listLoading.value = true
  try {
    const data = await listVisitorAuthApi({ userId: auth.userId })
    list.value = data.list || data.rows || data.data?.list || []
  } catch (e) {
    toastApiError(e, '加载列表失败')
    list.value = []
  } finally {
    listLoading.value = false
    refreshing.value = false
  }
}

async function generate() {
  genLoading.value = true
  try {
    const data = await createVisitorAuthApi({ userId: auth.userId, type: authType.value })
    currentToken.value = data.token || data.code || data.passphrase || ''
    if (!currentToken.value) {
      showToast('后端未返回口令字段')
      return
    }
    showSuccessToast('已生成')
    loadList()
  } catch (e) {
    toastApiError(e, '生成失败')
  } finally {
    genLoading.value = false
  }
}

async function copyToken() {
  try {
    await navigator.clipboard.writeText(currentToken.value)
    showToast('已复制')
  } catch {
    showToast('复制失败，请长按手动复制')
  }
}

function onRefresh() {
  refreshing.value = true
  loadList()
}

async function remove(item) {
  try {
    await deleteVisitorAuthApi(item.id)
    showToast('已删除')
    loadList()
  } catch (e) {
    toastApiError(e, '删除失败')
  }
}

onMounted(loadList)
</script>

<style scoped>
.pad {
  padding: 12px 16px;
}
.token {
  font-family: monospace;
  font-size: 15px;
  word-break: break-all;
}
.swipe-btn {
  height: 100%;
}
</style>
