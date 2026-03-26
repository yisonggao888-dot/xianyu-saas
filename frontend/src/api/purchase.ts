import request from '@/api/request'

// 创建采购任务
export const createPurchase = (data: {
  order_id: string
  source: string
  source_id: string
  source_url: string
  sku_spec?: string
  quantity?: number
  buyer_name: string
  buyer_phone: string
  buyer_address: string
}) => {
  return request.post('/purchases/create', data)
}

// 获取任务状态
export const getPurchaseTask = (taskId: string) => {
  return request.get(`/purchases/task/${taskId}`)
}

// 获取订单的采购任务
export const getOrderPurchaseTasks = (orderId: string) => {
  return request.get(`/purchases/order/${orderId}/tasks`)
}

// 取消任务
export const cancelPurchaseTask = (taskId: string) => {
  return request.post(`/purchases/task/${taskId}/cancel`)
}

// 获取队列统计
export const getPurchaseStats = () => {
  return request.get('/purchases/stats')
}
