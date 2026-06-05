import { createRouter, createWebHistory } from 'vue-router'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import { useUserStore } from '@/stores/user'

NProgress.configure({ showSpinner: false })

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/',
    name: 'Layout',
    component: () => import('@/layout/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '数据看板', icon: 'DataAnalysis' }
      },
      {
        path: 'user',
        name: 'UserManagement',
        component: () => import('@/views/user/UserView.vue'),
        meta: { title: '用户管理', icon: 'User' }
      },
      {
        path: 'device',
        name: 'DeviceManagement',
        component: () => import('@/views/device/DeviceView.vue'),
        meta: { title: '设备管理', icon: 'Monitor' }
      },
      {
        path: 'data',
        name: 'DataQuery',
        component: () => import('@/views/data/DataView.vue'),
        meta: { title: '数据查询', icon: 'DataLine' }
      },
      {
        path: 'alert',
        name: 'AlertCenter',
        component: () => import('@/views/alert/AlertView.vue'),
        meta: { title: '预警中心', icon: 'Warning' }
      },
      {
        path: 'ai',
        name: 'AiAnalysis',
        component: () => import('@/views/ai/AiView.vue'),
        meta: { title: 'AI智能分析', icon: 'TrendCharts' }
      },
      {
        path: 'ai/chat',
        name: 'AiChat',
        component: () => import('@/views/ai/AiChatView.vue'),
        meta: { title: 'AI健康助手', icon: 'ChatDotRound' }
      },
      {
        path: 'report',
        name: 'ReportCenter',
        component: () => import('@/views/report/ReportView.vue'),
        meta: { title: '报告中心', icon: 'Document' }
      },
      {
        path: 'archive',
        name: 'HealthArchive',
        component: () => import('@/views/archive/ArchiveView.vue'),
        meta: { title: '健康档案', icon: 'FolderOpened' }
      },
      {
        path: 'visualization',
        name: 'Visualization',
        component: () => import('@/views/visualization/VisualizationView.vue'),
        meta: { title: '数据大屏', icon: 'DataBoard' }
      },
      {
        path: 'settings',
        name: 'SystemSettings',
        component: () => import('@/views/settings/SettingsView.vue'),
        meta: { title: '系统设置', icon: 'Setting' }
      },
      {
        path: 'log',
        name: 'OperationLog',
        component: () => import('@/views/log/LogView.vue'),
        meta: { title: '操作日志', icon: 'List' }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/profile/ProfileView.vue'),
        meta: { title: '个人中心', icon: 'UserFilled' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  NProgress.start()
  
  document.title = to.meta.title ? `${to.meta.title} - 智康云枢` : '智康云枢'
  
  const userStore = useUserStore()
  
  if (to.meta.requiresAuth !== false && !userStore.isLoggedIn) {
    next('/login')
  } else if (to.path === '/login' && userStore.isLoggedIn) {
    next('/')
  } else {
    next()
  }
})

router.afterEach(() => {
  NProgress.done()
})

export default router
