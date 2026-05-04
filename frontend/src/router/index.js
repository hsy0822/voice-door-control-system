import { createRouter, createWebHashHistory } from 'vue-router'
import { showToast } from 'vant'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/', redirect: '/login' },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { guest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { guest: true },
  },
  {
    path: '/open-door',
    name: 'OpenDoor',
    component: () => import('@/views/OpenDoor.vue'),
    meta: { requiresAuth: true, roles: ['resident'] },
  },
  {
    path: '/voice-print',
    name: 'VoicePrint',
    component: () => import('@/views/VoicePrint.vue'),
    meta: { requiresAuth: true, roles: ['resident'] },
  },
  {
    path: '/user-center',
    name: 'UserCenter',
    component: () => import('@/views/UserCenter.vue'),
    meta: { requiresAuth: true, roles: ['resident'] },
  },
  {
    path: '/visitor-auth',
    name: 'VisitorAuth',
    component: () => import('@/views/VisitorAuth.vue'),
    meta: { requiresAuth: true, roles: ['resident'] },
  },
  {
    path: '/user-log',
    name: 'UserLog',
    component: () => import('@/views/UserLog.vue'),
    meta: { requiresAuth: true, roles: ['resident'] },
  },
  {
    path: '/admin',
    name: 'AdminConsole',
    component: () => import('@/views/AdminConsole.vue'),
    meta: { requiresAuth: true, roles: ['admin'] },
  },
  {
    path: '/admin/door-logs',
    name: 'AdminDoorLogs',
    component: () => import('@/views/AdminDoorLogs.vue'),
    meta: { requiresAuth: true, roles: ['admin'] },
  },
  {
    path: '/admin/residents',
    name: 'ResidentManage',
    component: () => import('@/views/ResidentManage.vue'),
    meta: { requiresAuth: true, roles: ['admin'] },
  },
  {
    path: '/admin/alarms',
    name: 'AlarmList',
    component: () => import('@/views/AlarmList.vue'),
    meta: { requiresAuth: true, roles: ['admin'] },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.guest && auth.isLoggedIn) {
    const dest = auth.role === 'admin' ? '/admin' : '/user-center'
    return dest
  }
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    showToast('请先登录')
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.roles?.length && auth.isLoggedIn) {
    if (!to.meta.roles.includes(auth.role)) {
      showToast('无权访问该页面')
      return auth.role === 'admin' ? '/admin' : '/user-center'
    }
  }
  return true
})

export default router
