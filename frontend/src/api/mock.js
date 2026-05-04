/**
 * 后端未就绪时，可在各页面暂时改用这里的占位数据或在前端拦截。
 * 默认仍走真实 http；开发联调请启动后端并匹配 src/api/index.js 路径。
 */

export function mockChallenge() {
  const a = Math.floor(Math.random() * 9) + 1
  const b = Math.floor(Math.random() * 9) + 1
  return {
    challengeId: `mock-${Date.now()}`,
    question: `${a}+${b} 等于几？`,
    passphrase: String(a + b),
  }
}
