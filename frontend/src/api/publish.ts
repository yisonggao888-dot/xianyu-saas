import request from '@/api/request'

// 发布商品到闲鱼
export const publishToXianyu = (data: {
  product_id: string
  account_id: string
  sale_price?: number
}) => {
  return request.post('/publish/publish', data)
}

// 批量发布
export const batchPublish = (data: {
  product_ids: string[]
  account_id: string
  interval?: number
}) => {
  return request.post('/publish/batch-publish', data)
}

// 获取分类列表
export const getCategories = () => {
  return request.get('/publish/categories')
}
