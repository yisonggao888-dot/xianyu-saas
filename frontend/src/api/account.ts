import api from './request'

export interface Account {
  id: string
  name: string
  xianyu_nickname?: string
  status: 'active' | 'paused' | 'error'
  last_online_at?: string
  message_count_this_month: number
  ai_enabled: boolean
  created_at: string
}

export interface AccountCreateData {
  name: string
  cookies: string
}

export interface AccountUpdateData {
  name?: string
  cookies?: string
  ai_enabled?: boolean
  status?: 'active' | 'paused' | 'error'
}

export const accountApi = {
  // 获取账号列表
  getList: (): Promise<Account[]> => {
    return api.get('/accounts/')
  },

  // 获取账号详情
  getDetail: (id: string) => {
    return api.get(`/accounts/${id}`)
  },

  // 创建账号
  create: (data: AccountCreateData) => {
    return api.post('/accounts/', data)
  },

  // 更新账号
  update: (id: string, data: AccountUpdateData) => {
    return api.put(`/accounts/${id}`, data)
  },

  // 删除账号
  delete: (id: string) => {
    return api.delete(`/accounts/${id}`)
  },
}
