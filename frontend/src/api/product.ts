import request from '@/api/request'

// 搜索商品
export const searchProducts = (data: {
  keyword: string
  sources?: string[]
  min_price?: number
  max_price?: number
  min_sales?: number
  sort?: string
}) => {
  return request.post('/products/search', data)
}

// 获取选品列表
export const getProductList = (params?: { status?: string }) => {
  return request.get('/products/list', { params })
}

// 获取商品详情
export const getProduct = (id: string) => {
  return request.get(`/products/${id}`)
}

// 添加选品
export const addToList = (data: {
  source: string
  source_id: string
  title: string
  cost_price: number
  sale_price: number
  main_image: string
  detail_url: string
  description?: string
}) => {
  return request.post('/products/add-to-list', data)
}

// 更新商品
export const updateProduct = (id: string, data: {
  title?: string
  sale_price?: number
  main_image?: string
  description?: string
  status?: string
}) => {
  return request.put(`/products/${id}`, data)
}

// 删除商品
export const deleteProduct = (id: string) => {
  return request.delete(`/products/${id}`)
}

// 获取选品统计
export const getProductStats = () => {
  return request.get('/products/stats/summary')
}
