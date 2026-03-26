import request from '@/api/request'

// 同步物流
export const syncLogistics = (orderId: string) => {
  return request.post('/logistics/sync', { order_id: orderId })
}

// 回填物流到闲鱼
export const fillLogisticsToXianyu = (data: {
  order_id: string
  tracking_number: string
  carrier: string
}) => {
  return request.post('/logistics/fill-to-xianyu', data)
}

// 触发批量同步
export const autoSyncAll = () => {
  return request.post('/logistics/auto-sync-all')
}
