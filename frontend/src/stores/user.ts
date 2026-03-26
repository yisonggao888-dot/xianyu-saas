import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { TokenResponse } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  // State
  const token = ref(localStorage.getItem('token') || '')
  const refreshToken = ref(localStorage.getItem('refreshToken') || '')
  const userInfo = ref<any>(null)

  // Getters
  const isLoggedIn = computed(() => !!token.value)

  // Actions
  const setToken = (data: TokenResponse) => {
    token.value = data.access_token
    refreshToken.value = data.refresh_token
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('refreshToken', data.refresh_token)
  }

  const clearToken = () => {
    token.value = ''
    refreshToken.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
  }

  const login = async (email: string, password: string) => {
    const data = await authApi.login({ email, password })
    setToken(data)
    return data
  }

  const register = async (email: string, password: string, tenant_name: string) => {
    const data = await authApi.register({ email, password, tenant_name })
    setToken(data)
    return data
  }

  const logout = () => {
    clearToken()
  }

  const fetchUserInfo = async () => {
    try {
      const data = await authApi.getMe()
      userInfo.value = data
      return data
    } catch (error) {
      return null
    }
  }

  return {
    token,
    refreshToken,
    userInfo,
    isLoggedIn,
    login,
    register,
    logout,
    fetchUserInfo,
    clearToken,
  }
})
