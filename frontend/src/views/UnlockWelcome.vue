<template>
  <div class="welcome-page" :class="{ ready: stage >= 1 }">
    <!-- 背景光效 -->
    <div class="bg-glow" />
    <div class="bg-grid" />
    <div class="particles">
      <span v-for="n in 12" :key="n" :style="particleStyle(n)" />
    </div>

    <!-- 门体 -->
    <div class="door-scene">
      <div class="door-frame">
        <div class="door-panel" :class="{ open: stage >= 3 }">
          <div class="door-inner">
            <div class="door-line" />
            <div class="door-line short" />
          </div>
        </div>
        <div class="door-light" :class="{ on: stage >= 3 }" />
      </div>

      <!-- 锁 -->
      <div class="lock-wrap" :class="{ unlocked: stage >= 2 }">
        <div class="lock-body">
          <div class="lock-shackle" />
          <div class="lock-keyhole" />
        </div>
        <div v-if="stage >= 2" class="lock-ring" />
      </div>
    </div>

    <!-- 成功图标 -->
    <div class="success-badge" :class="{ show: stage >= 2 }">
      <svg viewBox="0 0 52 52" class="check-svg">
        <circle class="check-circle" cx="26" cy="26" r="24" fill="none" />
        <path class="check-mark" fill="none" d="M14 27l8 8 16-18" />
      </svg>
    </div>

    <!-- 文案 -->
    <div class="copy">
      <p class="line status-line" :class="{ show: stage >= 1 }">验证成功</p>
      <h1 class="line title-line" :class="{ show: stage >= 2 }">
        欢迎回来，<span class="name">{{ displayName }}</span>
      </h1>
      <p class="line sub-line" :class="{ show: stage >= 3 }">门禁已开启 · 请通行</p>
      <p class="line time-line" :class="{ show: stage >= 4 }">{{ timeText }}</p>
    </div>

    <!-- 底部 -->
    <div class="footer" :class="{ show: stage >= 4 }">
      <div class="progress-track">
        <div class="progress-bar" :style="{ width: `${progress}%` }" />
      </div>
      <van-button type="primary" round block class="btn" @click="goNext">
        {{ countdown > 0 ? `${countdown}s 后自动返回` : '进入个人中心' }}
      </van-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const stage = ref(0)
const countdown = ref(5)
const progress = ref(0)
const timeText = ref('')

let stageTimers = []
let countTimer = null
let progressTimer = null

const displayName = computed(() => auth.user?.username || '住户')

const TOTAL_SEC = 5

function particleStyle(n) {
  const left = ((n * 17) % 100) + '%'
  const delay = (n * 0.35) % 3
  const size = 4 + (n % 3) * 2
  return {
    left,
    width: `${size}px`,
    height: `${size}px`,
    animationDelay: `${delay}s`,
  }
}

function formatNow() {
  const d = new Date()
  const pad = (x) => String(x).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function goNext() {
  clearTimers()
  router.replace('/user-center')
}

function clearTimers() {
  stageTimers.forEach(clearTimeout)
  stageTimers = []
  if (countTimer) clearInterval(countTimer)
  if (progressTimer) clearInterval(progressTimer)
  countTimer = null
  progressTimer = null
}

function startSequence() {
  timeText.value = formatNow()
  const steps = [400, 900, 1500, 2200]
  steps.forEach((ms, i) => {
    stageTimers.push(setTimeout(() => {
      stage.value = i + 1
    }, ms))
  })

  progress.value = 0
  const tick = 50
  const totalMs = TOTAL_SEC * 1000
  let elapsed = 0
  progressTimer = setInterval(() => {
    elapsed += tick
    progress.value = Math.min(100, (elapsed / totalMs) * 100)
  }, tick)

  countdown.value = TOTAL_SEC
  countTimer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) {
      clearInterval(countTimer)
      countTimer = null
      goNext()
    }
  }, 1000)
}

onMounted(() => {
  startSequence()
})

onUnmounted(clearTimers)
</script>

<style scoped>
.welcome-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px 20px 32px;
  box-sizing: border-box;
  background: linear-gradient(165deg, #0a1628 0%, #0d2847 45%, #102a52 100%);
  color: #fff;
}

.bg-glow {
  position: absolute;
  inset: -20%;
  background: radial-gradient(circle at 50% 35%, rgba(25, 137, 250, 0.35) 0%, transparent 55%);
  pointer-events: none;
  animation: glowPulse 3s ease-in-out infinite;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: radial-gradient(ellipse 80% 70% at 50% 40%, #000 20%, transparent 75%);
  pointer-events: none;
}

.particles {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.particles span {
  position: absolute;
  bottom: -10px;
  border-radius: 50%;
  background: rgba(125, 211, 252, 0.7);
  animation: floatUp 4s ease-in infinite;
  opacity: 0;
}

@keyframes floatUp {
  0% {
    transform: translateY(0) scale(0.6);
    opacity: 0;
  }
  15% {
    opacity: 0.9;
  }
  100% {
    transform: translateY(-100vh) scale(1);
    opacity: 0;
  }
}

@keyframes glowPulse {
  0%,
  100% {
    opacity: 0.85;
  }
  50% {
    opacity: 1;
  }
}

.door-scene {
  position: relative;
  width: 200px;
  height: 220px;
  margin-bottom: 8px;
  z-index: 1;
}

.door-frame {
  position: absolute;
  inset: 0;
  border: 3px solid rgba(125, 211, 252, 0.5);
  border-radius: 8px 8px 4px 4px;
  background: linear-gradient(180deg, #1a3a5c 0%, #0f2744 100%);
  box-shadow:
    0 0 40px rgba(25, 137, 250, 0.25),
    inset 0 0 30px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  perspective: 600px;
}

.door-panel {
  position: absolute;
  inset: 8px;
  background: linear-gradient(135deg, #2a5080 0%, #1e3d66 100%);
  border-radius: 4px;
  transform-origin: left center;
  transition: transform 1s cubic-bezier(0.34, 1.2, 0.64, 1);
  box-shadow: inset -8px 0 20px rgba(0, 0, 0, 0.25);
}

.door-panel.open {
  transform: rotateY(-68deg);
}

.door-inner {
  padding: 24px 16px;
}

.door-line {
  height: 3px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
  margin-bottom: 12px;
}

.door-line.short {
  width: 60%;
}

.door-light {
  position: absolute;
  right: -40px;
  top: 20%;
  width: 80px;
  height: 60%;
  background: linear-gradient(90deg, rgba(255, 230, 150, 0) 0%, rgba(255, 230, 150, 0.55) 100%);
  opacity: 0;
  transition: opacity 0.8s ease 0.3s;
  filter: blur(8px);
  pointer-events: none;
}

.door-light.on {
  opacity: 1;
}

.lock-wrap {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  transition: opacity 0.5s ease 0.6s;
}

.lock-wrap.unlocked {
  opacity: 0;
  pointer-events: none;
}

.lock-body {
  width: 44px;
  height: 36px;
  background: linear-gradient(180deg, #ffd666 0%, #faad14 100%);
  border-radius: 6px;
  position: relative;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
  animation: lockShake 0.5s ease 0.2s;
}

.lock-shackle {
  position: absolute;
  top: -18px;
  left: 50%;
  transform: translateX(-50%);
  width: 28px;
  height: 22px;
  border: 5px solid #faad14;
  border-bottom: none;
  border-radius: 14px 14px 0 0;
  transition: transform 0.6s cubic-bezier(0.34, 1.4, 0.64, 1) 0.5s;
}

.lock-wrap.unlocked .lock-shackle {
  transform: translateX(-50%) translateY(-8px) rotate(-22deg);
}

.lock-keyhole {
  position: absolute;
  bottom: 8px;
  left: 50%;
  transform: translateX(-50%);
  width: 8px;
  height: 10px;
  background: #5c3d00;
  border-radius: 50% 50% 40% 40%;
}

.lock-ring {
  position: absolute;
  inset: -20px;
  border: 2px solid rgba(7, 193, 96, 0.6);
  border-radius: 50%;
  animation: ringExpand 0.8s ease forwards;
}

@keyframes lockShake {
  0%,
  100% {
    transform: rotate(0);
  }
  25% {
    transform: rotate(-6deg);
  }
  75% {
    transform: rotate(6deg);
  }
}

@keyframes ringExpand {
  from {
    transform: scale(0.6);
    opacity: 1;
  }
  to {
    transform: scale(1.8);
    opacity: 0;
  }
}

.success-badge {
  position: relative;
  width: 72px;
  height: 72px;
  margin: -20px 0 16px;
  z-index: 3;
  opacity: 0;
  transform: scale(0.5);
  transition:
    opacity 0.5s ease,
    transform 0.6s cubic-bezier(0.34, 1.4, 0.64, 1);
}

.success-badge.show {
  opacity: 1;
  transform: scale(1);
}

.check-svg {
  width: 100%;
  height: 100%;
}

.check-circle {
  stroke: #07c160;
  stroke-width: 3;
  stroke-dasharray: 151;
  stroke-dashoffset: 151;
  animation: drawCircle 0.6s ease forwards 0.1s;
}

.check-mark {
  stroke: #07c160;
  stroke-width: 4;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 40;
  stroke-dashoffset: 40;
  animation: drawCheck 0.4s ease forwards 0.55s;
}

@keyframes drawCircle {
  to {
    stroke-dashoffset: 0;
  }
}

@keyframes drawCheck {
  to {
    stroke-dashoffset: 0;
  }
}

.copy {
  text-align: center;
  z-index: 1;
  width: 100%;
  max-width: 340px;
}

.line {
  margin: 0;
  opacity: 0;
  transform: translateY(16px);
  transition:
    opacity 0.55s ease,
    transform 0.55s cubic-bezier(0.22, 1, 0.36, 1);
}

.line.show {
  opacity: 1;
  transform: translateY(0);
}

.status-line {
  font-size: 14px;
  letter-spacing: 0.2em;
  color: #7dd3fc;
  margin-bottom: 10px;
}

.title-line {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.4;
  margin-bottom: 8px;
}

.name {
  color: #ffd666;
}

.sub-line {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.75);
  margin-bottom: 6px;
}

.time-line {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  font-variant-numeric: tabular-nums;
}

.footer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 16px 20px calc(16px + env(safe-area-inset-bottom));
  background: linear-gradient(transparent, rgba(10, 22, 40, 0.92) 30%);
  opacity: 0;
  transform: translateY(12px);
  transition:
    opacity 0.5s ease 0.2s,
    transform 0.5s ease 0.2s;
  z-index: 5;
}

.footer.show {
  opacity: 1;
  transform: translateY(0);
}

.progress-track {
  height: 3px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
  margin-bottom: 14px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #1989fa, #07c160);
  border-radius: 2px;
  transition: width 0.05s linear;
}

.btn {
  --van-button-primary-background: #1989fa;
  box-shadow: 0 6px 20px rgba(25, 137, 250, 0.35);
}
</style>
