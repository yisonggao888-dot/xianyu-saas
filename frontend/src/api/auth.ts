import api from './request'

export interface LoginData {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
  tenant_name: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export const authApi = {
  // 登录
  login: (data: LoginData): Promise<TokenResponse> => {
    return api.post('/auth/login', data)
  },

  // 注册
  register: (data: RegisterData): Promise<TokenResponse> => {
    return api.post('/auth/register', data)
  },

  // 刷新token
  refreshToken: (refreshToken: string): Promise<TokenResponse> => {
    return api.post('/auth/refresh', { refresh_token: refreshToken })
  },

  // 获取当前用户信息
  getMe: () => {
    return api.get('/auth/me')
  },
}
