/** Web Audio → mono PCM → WAV @ 16kHz */

const TARGET_RATE = 16000
const MIN_SEC = 1
const MAX_SEC = 5

function mergeFloat32(chunks) {
  let n = 0
  for (const c of chunks) n += c.length
  const out = new Float32Array(n)
  let o = 0
  for (const c of chunks) {
    out.set(c, o)
    o += c.length
  }
  return out
}

function resampleLinear(input, fromRate, toRate) {
  if (fromRate === toRate) return input
  const ratio = fromRate / toRate
  const outLen = Math.max(1, Math.floor(input.length / ratio))
  const out = new Float32Array(outLen)
  for (let i = 0; i < outLen; i++) {
    const srcPos = i * ratio
    const j = Math.floor(srcPos)
    const f = srcPos - j
    const a = input[j] ?? 0
    const b = input[j + 1] ?? a
    out[i] = a + (b - a) * f
  }
  return out
}

function trimToMaxSeconds(samples, sampleRate, maxSec) {
  const max = Math.floor(sampleRate * maxSec)
  if (samples.length <= max) return samples
  return samples.subarray(0, max)
}

function floatTo16BitPCM(float32) {
  const buf = new ArrayBuffer(float32.length * 2)
  const view = new DataView(buf)
  let offset = 0
  for (let i = 0; i < float32.length; i++, offset += 2) {
    let s = Math.max(-1, Math.min(1, float32[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
  }
  return buf
}

function writeWavHeader(sampleRate, numSamples) {
  const blockAlign = 2
  const byteRate = sampleRate * blockAlign
  const dataSize = numSamples * 2
  const buffer = new ArrayBuffer(44)
  const v = new DataView(buffer)
  const writeStr = (off, s) => {
    for (let i = 0; i < s.length; i++) v.setUint8(off + i, s.charCodeAt(i))
  }
  writeStr(0, 'RIFF')
  v.setUint32(4, 36 + dataSize, true)
  writeStr(8, 'WAVE')
  writeStr(12, 'fmt ')
  v.setUint32(16, 16, true)
  v.setUint16(20, 1, true)
  v.setUint16(22, 1, true)
  v.setUint32(24, sampleRate, true)
  v.setUint32(28, byteRate, true)
  v.setUint16(32, blockAlign, true)
  v.setUint16(34, 16, true)
  writeStr(36, 'data')
  v.setUint32(40, dataSize, true)
  return buffer
}

export function encodeWavBlob(samples16kMono) {
  const pcm = floatTo16BitPCM(samples16kMono)
  const header = writeWavHeader(TARGET_RATE, samples16kMono.length)
  return new Blob([header, pcm], { type: 'audio/wav' })
}

export { TARGET_RATE, MIN_SEC, MAX_SEC }

export class HoldWavRecorder {
  constructor() {
    this._ctx = null
    this._stream = null
    this._processor = null
    this._source = null
    this._gain = null
    this._chunks = []
    this._startedAt = 0
    this._maxTimer = null
  }

  async start(onLevel) {
    this._chunks = []
    this._stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    })
    this._ctx = new AudioContext({ sampleRate: TARGET_RATE })
    const actual = this._ctx.sampleRate
    this._source = this._ctx.createMediaStreamSource(this._stream)
    const bufferSize = 4096
    this._processor = this._ctx.createScriptProcessor(bufferSize, 1, 1)
    this._processor.onaudioprocess = (e) => {
      const input = e.inputBuffer.getChannelData(0)
      this._chunks.push(new Float32Array(input))
      if (typeof onLevel === 'function') {
        let sum = 0
        for (let i = 0; i < input.length; i++) sum += input[i] * input[i]
        onLevel(Math.sqrt(sum / input.length))
      }
    }
    this._gain = this._ctx.createGain()
    this._gain.gain.value = 0
    this._source.connect(this._processor)
    this._processor.connect(this._gain)
    this._gain.connect(this._ctx.destination)
    this._startedAt = this._ctx.currentTime
    if (this._maxTimer) clearTimeout(this._maxTimer)
    this._maxTimer = setTimeout(() => {
      window.dispatchEvent(new CustomEvent('voice-recorder-max-duration'))
    }, MAX_SEC * 1000)
  }

  _cleanup() {
    if (this._maxTimer) {
      clearTimeout(this._maxTimer)
      this._maxTimer = null
    }
    try {
      this._processor?.disconnect()
      this._source?.disconnect()
      this._gain?.disconnect()
    } catch (_) {}
    this._processor = null
    this._source = null
    this._gain = null
    if (this._stream) {
      this._stream.getTracks().forEach((t) => t.stop())
      this._stream = null
    }
    if (this._ctx) {
      this._ctx.close().catch(() => {})
      this._ctx = null
    }
  }

  /**
   * @returns {{ blob: Blob, durationSec: number, ok: boolean, reason?: string }}
   */
  stop() {
    const ctx = this._ctx
    let durationSec = 0
    if (ctx) durationSec = Math.max(0, ctx.currentTime - this._startedAt)

    let merged = mergeFloat32(this._chunks)
    const rate = ctx?.sampleRate ?? TARGET_RATE
    merged = resampleLinear(merged, rate, TARGET_RATE)
    merged = trimToMaxSeconds(merged, TARGET_RATE, MAX_SEC)

    this._cleanup()

    if (durationSec < MIN_SEC) {
      return { blob: null, durationSec, ok: false, reason: `录音不足 ${MIN_SEC} 秒` }
    }
    const blob = encodeWavBlob(merged)
    return { blob, durationSec: Math.min(durationSec, MAX_SEC), ok: true }
  }

  dispose() {
    this._cleanup()
  }
}
