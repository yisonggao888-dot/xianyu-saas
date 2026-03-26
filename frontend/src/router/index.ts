import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('./views/auth/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('./views/auth/Register.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    name: 'Layout',
    component: () => import('./views/layout/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('./views/dashboard/Dashboard.vue'),
        meta: { title: '首页' },
      },
      {
        path: 'accounts',
        name: 'Accounts',
        component: () => import('./views/accounts/AccountList.vue'),
        meta: { title: '闲鱼账号' },
      },
      {
        path: 'conversations',
        name: 'Conversations',
        component: () => import('./views/conversations/ConversationList.vue'),
        meta: { title: '对话管理' },
      },
      {
        path: 'products',
        name: 'Products',
        component: () => import('./views/products/ProductList.vue'),
        meta: { title: '选品中心' },
      },
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('./views/orders/OrderList.vue'),
        meta: { title: '订单管理' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('./views/settings/Settings.vue'),
        meta: { title: '系统设置' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('./views/error/NotFound.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  
  if (!to.meta.public && !token) {
    next('/login')
  } else if ((to.path === '/login' || to.path === '/register') && token) {
    next('/')
  } else {
    next()
  }
})

export default router
