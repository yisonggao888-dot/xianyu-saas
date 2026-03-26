import request from '@/api/request'

// 获取订单列表
export const getOrderList = (params?: {
  status?: string
  days?: number
}) => {
  return request.get('/orders/', { params })
}

// 获取订单详情
export const getOrder = (id: string) => {
  return request.get(`/orders/${id}`)
}

// 创建订单
export const createOrder = (data: {
  conversation_id: string
  xianyu_order_id: string
  buyer_id: string
  item_title: string
  sold_price: number
  cost_price: number
}) => {
  return request.post('/orders/', data)
}

// 更新订单状态
export const updateOrderStatus = (id: string, data: {
  status: string
  tracking_number?: string
}) => {
  return request.put(`/orders/${id}/status`, data)
}

// 更新货源信息
export const updateSourceInfo = (id: string, data: {
  source_platform: string
  source_order_id: string
}) => {
  return request.put(`/orders/${id}/source`, data)
}

// 自动采购
export const autoPurchase = (orderId: string, productId: string) => {
  return request.post(`/orders/${orderId}/purchase`, null, {
    params: { product_id: productId }
  })
}

// 获取订单统计
export const getOrderStats = (days?: number) => {
  return request.get('/orders/stats/summary', { params: { days } })
}

// 获取每日统计
export const getDailyStats = (days?: number) => {
  return request.get('/orders/stats/daily', { params: { days } })
}
