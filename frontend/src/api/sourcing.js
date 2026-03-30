import request from './request'

export const sourcingApi = {
  // 搜索商品
  searchProducts(data) {
    return request.post('/sourcing/search', data)
  },

  // 获取爆款商品
  getHotProducts(params) {
    return request.get('/sourcing/hot-products', { params })
  },

  // 获取分类分析
  getCategoryAnalysis() {
    return request.get('/sourcing/analysis/category')
  },

  // 获取价格分析
  getPriceAnalysis(category) {
    return request.get('/sourcing/analysis/price', { params: { category } })
  },

  // 分析商品
  analyzeProducts() {
    return request.post('/sourcing/analyze')
  },

  // 添加到商品中心
  addToCenter(data) {
    return request.post('/sourcing/add-to-center', data)
  },

  // 批量发布
  batchPublish(data) {
    return request.post('/sourcing/batch-publish', data)
  },

  // 获取发布任务列表
  getPublishTasks() {
    return request.get('/sourcing/publish-tasks')
  },

  // 获取任务进度
  getTaskProgress(taskId) {
    return request.get(`/sourcing/publish-tasks/${taskId}`)
  },

  // 取消任务
  cancelTask(taskId) {
    return request.post(`/sourcing/publish-tasks/${taskId}/cancel`)
  },

  // AI优化标题
  optimizeTitle(data) {
    return request.post('/sourcing/optimize-title', data)
  },

  // 创建擦亮计划
  createPolishSchedule(data) {
    return request.post('/sourcing/polish-schedules', data)
  },

  // 获取擦亮计划列表
  getPolishSchedules() {
    return request.get('/sourcing/polish-schedules')
  },

  // 获取擦亮计划详情
  getPolishScheduleDetail(scheduleId) {
    return request.get(`/sourcing/polish-schedules/${scheduleId}`)
  },

  // 暂停擦亮计划
  pausePolishSchedule(scheduleId) {
    return request.post(`/sourcing/polish-schedules/${scheduleId}/pause`)
  },

  // 恢复擦亮计划
  resumePolishSchedule(scheduleId) {
    return request.post(`/sourcing/polish-schedules/${scheduleId}/resume`)
  },

  // 删除擦亮计划
  deletePolishSchedule(scheduleId) {
    return request.delete(`/sourcing/polish-schedules/${scheduleId}`)
  },

  // 手动擦亮
  manualPolish(data) {
    return request.post('/sourcing/manual-polish', data)
  },
}
