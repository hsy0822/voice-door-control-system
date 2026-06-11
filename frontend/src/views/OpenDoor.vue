<template>
  <div class="page-safe open-door">
    <van-nav-bar title="开门鉴权" left-arrow @click-left="$router.push('/user-center')" />

    <div class="who">
      <van-tag type="primary" plain>{{ auth.user?.username }}</van-tag>
      <span class="role-text">住户</span>
    </div>

    <section class="challenge-box">
      <p class="hint">请看清题目后，按住下方按钮朗读答案</p>
      <div class="question">{{ challenge.question || '加载口令中…' }}</div>
      <van-button size="small" type="primary" plain round @click="refreshChallenge" :loading="chLoading">
        刷新口令
      </van-button>
    </section>

    <div class="rec-wrap">
      <button
        type="button"
        class="hold-btn"
        :class="{ active: holding, pulse: holding }"
        @mousedown.prevent="onPressStart"
        @mouseup.prevent="onPressEnd"
        @mouseleave.prevent="onPressLeave"
        @touchstart.prevent="onPressStart"
        @touchend.prevent="onPressEnd"
        @touchcancel.prevent="onPressEnd"
      >
        {{ holding ? '松开结束' : '按住录音' }}
      </button>
      <p class="status">{{ recordStatus }}</p>
      <div v-if="holding" class="meter">
        <span :style="{ width: `${Math.min(100, level * 400)}%` }" />
      </div>
    </div>

    <van-overlay :show="phase === 'upload' || phase === 'ai'" z-index="9999">
      <div class="overlay-inner">
        <van-loading vertical>{{ phase === 'upload' ? '音频上传中…' : 'AI 识别中…' }}</van-loading>
      </div>
    </van-overlay>

    <transition name="van-fade">
      <div v-if="result.show && !result.ok" class="result-panel">
        <div class="fail">
          <div class="cross">✕</div>
          <p>{{ result.reason }}</p>
        </div>
        <van-button type="primary" block round hairline @click="resetResult">知道了</van-button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useAuthStore } from '@/stores/auth'
import { fetchChallengeApi, verifyDoorApi } from '@/api/index'
import { toastApiError } from '@/api/http'
import { mockChallenge } from '@/api/mock'
import { HoldWavRecorder } from '@/utils/wavRecorder'

const auth = useAuthStore()
const router = useRouter()

const challenge = ref({ question: '', challengeId: '', passphrase: '' })
const chLoading = ref(false)
const holding = ref(false)
const recordStatus = ref('按住按钮开始录音')
const level = ref(0)
const phase = ref('idle')
const result = ref({ show: false, ok: false, reason: '' })

let recorder = null
let maxHandler = null

const innerQuestion = computed(() => challenge.value.question)

async function refreshChallenge() {
  chLoading.value = true
  try {
    const data = await fetchChallengeApi()
    challenge.value = {
      question: data.question ?? data.data?.question ?? '',
      challengeId: data.challengeId ?? data.id ?? '',
      passphrase: data.passphrase ?? data.answer ?? '',
    }
    if (!challenge.value.question) {
      const m = mockChallenge()
      challenge.value = { question: m.question, challengeId: m.challengeId, passphrase: m.passphrase }
      showToast('已使用本地演示口令（后端未返回题目）')
    }
  } catch (e) {
    const m = mockChallenge()
    challenge.value = { question: m.question, challengeId: m.challengeId, passphrase: m.passphrase }
    showToast('口令接口不可用，已切换演示数据')
  } finally {
    chLoading.value = false
  }
}

function onPressStart() {
  if (phase.value !== 'idle' && phase.value !== 'done') return
  holding.value = true
  recordStatus.value = '正在录音…'
  level.value = 0
  recorder = new HoldWavRecorder()
  maxHandler = () => {
    if (holding.value) onPressEnd()
  }
  window.addEventListener('voice-recorder-max-duration', maxHandler)
  recorder.start((lv) => {
    level.value = lv
  }).catch(() => {
    holding.value = false
    recordStatus.value = '无法访问麦克风'
    showToast('请允许麦克风权限')
  })
}

async function onPressEnd() {
  if (!holding.value || !recorder) return
  holding.value = false
  window.removeEventListener('voice-recorder-max-duration', maxHandler)
  maxHandler = null
  const r = recorder.stop()
  recorder = null
  if (!r.ok || !r.blob) {
    recordStatus.value = '录音完成'
    showToast(r.reason || '录音无效')
    return
  }
  recordStatus.value = '录音完成'
  await uploadAndVerify(r.blob)
}

function onPressLeave() {
  if (holding.value) onPressEnd()
}

function isDuress(payload) {
  return !!(payload?.duress || payload?.coercion || payload?.emotion === 'coercion')
}

function goUnlockWelcome() {
  router.push('/unlock-welcome')
}

async function uploadAndVerify(blob) {
  if (!(blob instanceof Blob) || blob.size === 0) {
    showToast('无效的录音文件')
    return
  }
  phase.value = 'upload'
  try {
    phase.value = 'ai'
    const uid = auth.userId
    const res = await verifyDoorApi({
      userId: uid,
      challengeId: challenge.value.challengeId,
      passphrase: innerQuestion.value,
      file: blob,
    })

    if (isDuress(res)) {
      goUnlockWelcome()
      phase.value = 'idle'
      return
    }

    const ok = res.success === true || res.code === 0 || res.data?.success === true
    if (ok) {
      showToast({ type: 'success', message: '开门成功' })
      goUnlockWelcome()
    } else {
      const reason =
        res.reason ||
        res.message ||
        (res.failType === 'passphrase' ? '口令错误' : '') ||
        (res.failType === 'voice' ? '声纹不匹配' : '') ||
        '验证失败'
      result.value = { show: true, ok: false, reason }
      showToast(reason)
    }
  } catch (e) {
    toastApiError(e, '上传或识别失败')
  } finally {
    phase.value = 'idle'
  }
}

function resetResult() {
  result.value = { show: false, ok: false, reason: '' }
}

onMounted(() => {
  refreshChallenge()
})

onUnmounted(() => {
  window.removeEventListener('voice-recorder-max-duration', maxHandler)
  recorder?.dispose?.()
})
</script>

<style scoped>
.open-door {
  padding-bottom: 24px;
}
.who {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
}
.role-text {
  color: #646566;
  font-size: 13px;
}
.challenge-box {
  margin: 8px 16px;
  padding: 20px;
  background: linear-gradient(135deg, #e8f4ff 0%, #fff 100%);
  border-radius: 12px;
  text-align: center;
  border: 1px solid #bcdcff;
}
.hint {
  margin: 0 0 12px;
  color: #646566;
  font-size: 13px;
}
.question {
  font-size: 26px;
  font-weight: 700;
  color: #1989fa;
  margin-bottom: 14px;
  line-height: 1.35;
}
.rec-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 16px;
}
.hold-btn {
  width: 160px;
  height: 160px;
  border-radius: 50%;
  border: none;
  background: #1989fa;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  box-shadow: 0 8px 24px rgba(25, 137, 250, 0.35);
  touch-action: manipulation;
}
.hold-btn.active {
  background: #0570c9;
  transform: scale(0.98);
}
.hold-btn.pulse {
  animation: pulse 1.2s infinite;
}
@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(25, 137, 250, 0.45);
  }
  70% {
    box-shadow: 0 0 0 18px rgba(25, 137, 250, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(25, 137, 250, 0);
  }
}
.status {
  margin-top: 16px;
  color: #646566;
  font-size: 14px;
}
.meter {
  margin-top: 10px;
  width: 200px;
  height: 6px;
  background: #eee;
  border-radius: 3px;
  overflow: hidden;
}
.meter span {
  display: block;
  height: 100%;
  background: #1989fa;
  transition: width 0.08s linear;
}
.overlay-inner {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #fff;
}
.result-panel {
  position: fixed;
  left: 16px;
  right: 16px;
  bottom: 24px;
  padding: 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.12);
  z-index: 10000;
  text-align: center;
}
.fail .cross {
  font-size: 48px;
  color: #ee0a24;
  font-weight: 700;
}
</style>
