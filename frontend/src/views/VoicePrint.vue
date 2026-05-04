<template>
  <div class="page-safe">
    <van-nav-bar title="声纹录入" left-arrow @click-left="$router.back()" />

    <van-notice-bar left-icon="volume-o" wrapable :scrollable="false">
      请<strong>匀速朗读</strong>系统给出的 3 段随机文字，每段单独录制；环境尽量安静。
    </van-notice-bar>

    <div class="toolbar">
      <van-button size="small" plain type="primary" round icon="replay" @click="rerollPrompts">
        换一组随机文本
      </van-button>
    </div>

    <div class="prompts">
      <div v-for="(t, i) in prompts" :key="`${i}-${t}`" class="seg">
        <div class="seg-head">
          <span class="idx">第 {{ i + 1 }} 段</span>
          <van-tag v-if="blobs[i]" type="success">已录</van-tag>
          <van-tag v-else type="warning">待录</van-tag>
        </div>
        <p class="seg-text">{{ t }}</p>
        <button
          type="button"
          class="mini-hold"
          :class="{ on: holdingIdx === i }"
          @mousedown.prevent="startSeg(i)"
          @mouseup.prevent="stopSeg(i)"
          @mouseleave.prevent="holdingIdx === i && stopSeg(i)"
          @touchstart.prevent="startSeg(i)"
          @touchend.prevent="stopSeg(i)"
        >
          {{ holdingIdx === i ? '松开结束' : '按住录制本段' }}
        </button>
        <div v-if="holdingIdx === i" class="wave">
          <span /><span /><span /><span /><span />
        </div>
      </div>
    </div>

    <div class="pad">
      <van-button type="primary" block round :disabled="!allReady" :loading="loading" @click="submit">
        提交录入
      </van-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { showToast, showSuccessToast, showFailToast, showConfirmDialog } from 'vant'
import { useRouter } from 'vue-router'
import { fetchVoiceprintPromptsApi, submitVoiceprintApi } from '@/api/index'
import { toastApiError } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { HoldWavRecorder } from '@/utils/wavRecorder'
import { pickRandomVoiceprintPrompts } from '@/utils/voiceprintPrompts'

const auth = useAuthStore()
const router = useRouter()

const prompts = ref(['加载中…', '…', '…'])
const blobs = ref([null, null, null])
const holdingIdx = ref(-1)
const loading = ref(false)

let recorder = null
let maxEv = null

const allReady = computed(() => blobs.value.every(Boolean))

async function loadPrompts() {
  try {
    const data = await fetchVoiceprintPromptsApi()
    const list = data.segments || data.prompts || data.lines || data.data?.segments
    if (Array.isArray(list) && list.length >= 3) {
      prompts.value = list.slice(0, 3)
      return
    }
  } catch (_) {}
  prompts.value = pickRandomVoiceprintPrompts(3)
  showToast('未连接后端，已从本地词库随机抽取 3 段')
}

function rerollPrompts() {
  const hasAny = blobs.value.some(Boolean)
  if (hasAny) {
    showConfirmDialog({
      title: '更换朗读文本',
      message: '更换后将清空已录制的三段音频，是否继续？',
    })
      .then(() => {
        blobs.value = [null, null, null]
        prompts.value = pickRandomVoiceprintPrompts(3)
        showToast('已换新的一组文本')
      })
      .catch(() => {})
    return
  }
  prompts.value = pickRandomVoiceprintPrompts(3)
  showToast('已换新的一组文本')
}

function startSeg(i) {
  if (holdingIdx.value !== -1) return
  holdingIdx.value = i
  recorder = new HoldWavRecorder()
  maxEv = () => {
    if (holdingIdx.value === i) stopSeg(i)
  }
  window.addEventListener('voice-recorder-max-duration', maxEv)
  recorder.start().catch(() => {
    holdingIdx.value = -1
    showToast('请允许麦克风权限')
  })
}

function stopSeg(i) {
  if (holdingIdx.value !== i || !recorder) return
  window.removeEventListener('voice-recorder-max-duration', maxEv)
  maxEv = null
  const r = recorder.stop()
  recorder = null
  holdingIdx.value = -1
  if (!r.ok || !r.blob) {
    showToast(r.reason || '本段录音无效')
    return
  }
  blobs.value[i] = r.blob
  blobs.value = [...blobs.value]
  showToast({ type: 'success', message: `第 ${i + 1} 段已完成` })
}

async function submit() {
  if (!allReady.value) {
    showToast('请先完成 3 段录音')
    return
  }
  loading.value = true
  try {
    await submitVoiceprintApi({ userId: auth.userId, files: blobs.value })
    showSuccessToast('声纹录入成功')
    router.replace('/user-center')
  } catch (e) {
    toastApiError(e, '录入失败')
    showFailToast('录入失败，请重试')
  } finally {
    loading.value = false
  }
}

onMounted(loadPrompts)

onUnmounted(() => {
  window.removeEventListener('voice-recorder-max-duration', maxEv)
  recorder?.dispose?.()
})
</script>

<style scoped>
.toolbar {
  padding: 10px 16px 0;
  display: flex;
  justify-content: flex-end;
}
.prompts {
  padding: 12px 16px 0;
}
.seg {
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 12px;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.06);
}
.seg-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.idx {
  font-weight: 600;
  color: #323233;
}
.seg-text {
  margin: 0 0 12px;
  color: #646566;
  line-height: 1.6;
  font-size: 15px;
}
.mini-hold {
  width: 100%;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #1989fa;
  background: #fff;
  color: #1989fa;
  font-size: 15px;
  touch-action: manipulation;
}
.mini-hold.on {
  background: #1989fa;
  color: #fff;
}
.wave {
  display: flex;
  gap: 4px;
  justify-content: center;
  margin-top: 10px;
  height: 22px;
  align-items: flex-end;
}
.wave span {
  width: 4px;
  background: #1989fa;
  border-radius: 2px;
  animation: bounce 0.7s ease infinite;
}
.wave span:nth-child(2) {
  animation-delay: 0.1s;
}
.wave span:nth-child(3) {
  animation-delay: 0.2s;
}
.wave span:nth-child(4) {
  animation-delay: 0.3s;
}
.wave span:nth-child(5) {
  animation-delay: 0.4s;
}
@keyframes bounce {
  0%,
  100% {
    height: 6px;
  }
  50% {
    height: 20px;
  }
}
.pad {
  padding: 16px;
}
</style>
