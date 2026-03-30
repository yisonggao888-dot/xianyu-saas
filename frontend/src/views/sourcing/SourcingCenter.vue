<template>
  <div class="sourcing-center">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>选品中心</h2>
      <p class="subtitle">从拼多多、1688等平台筛选爆款商品，一键上架到闲鱼</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <el-card class="stat-card" v-for="stat in stats" :key="stat.key">
        <div class="stat-value">{{ stat.value }}</div>
        <div class="stat-label">{{ stat.label }}</div>
      </el-card>
    </div>

    <!-- 搜索区域 -->
    <el-card class="search-card">
      <div class="search-form">
        <el-input
          v-model="searchForm.keyword"
          placeholder="输入关键词搜索商品，如：蓝牙耳机、手机壳..."
          size="large"
          class="keyword-input"
          @keyup.enter="handleSearch"
        >
          <template #append>
            <el-button type="primary" @click="handleSearch" :loading="searchLoading">
              <el-icon><Search /></el-icon>搜索
            </el-button>
          </template>
        </el-input>

        <div class="filter-row">
          <el-select v-model="searchForm.sources" multiple placeholder="选择平台" size="default">
            <el-option label="拼多多" value="pdd" />
            <el-option label="1688" value="1688" />
          </el-select>

          <el-input-number
            v-model="searchForm.minPrice"
            :min="0"
            placeholder="最低价"
            size="default"
          />
          <span class="price-separator">-</span>
          <el-input-number
            v-model="searchForm.maxPrice"
            :min="0"
            placeholder="最高价"
            size="default"
          />

          <el-select v-model="searchForm.sort" placeholder="排序方式" size="default">
            <el-option label="综合排序" value="default" />
            <el-option label="价格从低到高" value="price_asc" />
            <el-option label="价格从高到低" value="price_desc" />
            <el-option label="销量优先" value="sales" />
          </el-select>

          <el-button @click="showAdvancedFilter = !showAdvancedFilter">
            高级筛选<el-icon class="el-icon--right"><ArrowDown v-if="!showAdvancedFilter" /><ArrowUp v-else /></el-icon>
          </el-button>
        </div>

        <!-- 高级筛选 -->
        <el-collapse-transition>
          <div v-show="showAdvancedFilter" class="advanced-filter">
            <el-form :model="hotFilter" label-width="120px">
              <el-row :gutter="20">
                <el-col :span="8">
                  <el-form-item label="最低月销量">
                    <el-input-number v-model="hotFilter.minMonthlySales" :min="0" :step="10" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="最低利润率(%)">
                    <el-input-number v-model="hotFilter.minProfitMargin" :min="0" :max="100" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="最低评分">
                    <el-rate v-model="hotFilter.minRating" :max="5" allow-half />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="20">
                <el-col :span="8">
                  <el-form-item label="最大竞争度">
                    <el-slider v-model="hotFilter.maxCompetition" :max="1" :step="0.1" show-stops />
                  </el-form-item>
                </el-col>
                <el-col :span="16">
                  <el-form-item>
                    <el-button type="primary" @click="getHotProducts">获取爆款</el-button>
                    <el-button @click="resetFilter">重置</el-button>
                  </el-form-item>
                </el-col>
              </el-row>
            </el-form>
          </div>
        </el-collapse-transition>
      </div>
    </el-card>

    <!-- 结果区域 -->
    <el-card class="results-card" v-loading="searchLoading">
      <template #header>
        <div class="results-header">
          <span>搜索结果 ({{ totalCount }}件商品)</span>
          <div class="header-actions">
            <el-button type="primary" @click="openBatchPublish" :disabled="selectedProducts.length === 0">
              批量发布 ({{ selectedProducts.length }})
            </el-button>
            <el-button @click="analyzeProducts" :loading="analyzing">
              <el-icon><DataAnalysis /></el-icon>数据分析
            </el-button>
          </div>
        </div>
      </template>

      <!-- 平台标签页 -->
      <el-tabs v-model="activeTab" type="border-card">
        <el-tab-pane label="全部" name="all">
          <ProductList
            :products="allProducts"
            :loading="searchLoading"
            @select="handleSelect"
            @add-to-center="addToCenter"
            @optimize-title="optimizeTitle"
          />
        </el-tab-pane>
        <el-tab-pane label="拼多多" name="pdd">
          <ProductList
            :products="pddProducts"
            :loading="searchLoading"
            @select="handleSelect"
            @add-to-center="addToCenter"
            @optimize-title="optimizeTitle"
          />
        </el-tab-pane>
        <el-tab-pane label="1688" name="1688">
          <ProductList
            :products="ali1688Products"
            :loading="searchLoading"
            @select="handleSelect"
            @add-to-center="addToCenter"
            @optimize-title="optimizeTitle"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 批量发布对话框 -->
    <el-dialog
      v-model="batchPublishVisible"
      title="批量发布到闲鱼"
      width="600px"
    >
      <el-form :model="batchForm" label-width="100px">
        <el-form-item label="任务名称">
          <el-input v-model="batchForm.name" placeholder="如：蓝牙耳机批量发布" />
        </el-form-item>
        <el-form-item label="目标账号">
          <el-select
            v-model="batchForm.targetAccounts"
            multiple
            placeholder="选择要发布的账号"
            style="width: 100%"
          >
            <el-option
              v-for="account in accounts"
              :key="account.id"
              :label="account.name"
              :value="account.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="加价比例">
          <el-slider v-model="batchForm.priceMarkup" :min="1" :max="3" :step="0.1" show-input />
        </el-form-item>
        <el-form-item label="图片处理">
          <el-checkbox v-model="batchForm.addWatermark">添加水印</el-checkbox>
          <el-checkbox v-model="batchForm.compressImages">压缩图片</el-checkbox>
          <el-checkbox v-model="batchForm.removeDuplicates">去重</el-checkbox>
        </el-form-item>
        <el-form-item label="标题优化">
          <el-checkbox v-model="batchForm.optimizeTitle">使用AI优化标题</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchPublishVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmBatchPublish" :loading="publishing">
          确认发布
        </el-button>
      </template>
    </el-dialog>

    <!-- 标题优化对话框 -->
    <el-dialog
      v-model="optimizeDialogVisible"
      title="AI标题优化"
      width="500px"
    >
      <div v-if="optimizing" class="optimize-loading">
        <el-skeleton :rows="3" animated />
        <p>正在使用AI优化标题...</p>
      </div>
      <div v-else-if="optimizeResult" class="optimize-result">
        <div class="original-title">
          <label>原标题：</label>
          <p>{{ optimizeResult.original_title }}</p>
        </div>
        <div class="optimized-title">
          <label>优化后：</label>
          <el-input
            v-model="optimizeResult.optimized_title"
            type="textarea"
            :rows="2"
          />
        </div>
        <div class="optimize-score">
          <label>优化得分：</label>
          <el-rate
            v-model="optimizeResult.score"
            :max="100"
            :colors="['#99A9BF', '#F7BA2A', '#FF9900']"
            disabled
          />
          <span>{{ optimizeResult.score }}分</span>
        </div>
        <div class="optimize-keywords">
          <label>提取关键词：</label>
          <el-tag v-for="kw in optimizeResult.keywords" :key="kw" size="small" class="keyword-tag">
            {{ kw }}
          </el-tag>
        </div>
        <div class="optimize-improvements">
          <label>改进点：</label>
          <ul>
            <li v-for="(imp, idx) in optimizeResult.improvements" :key="idx">{{ imp }}</li>
          </ul>
        </div>
      </div>
      <template #footer>
        <el-button @click="optimizeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="applyOptimizedTitle" :disabled="!optimizeResult">
          应用优化
        </el-button>
      </template>
    </el-dialog>

    <!-- 任务进度对话框 -->
    <el-dialog
      v-model="taskProgressVisible"
      title="发布任务进度"
      width="500px"
      :close-on-click-modal="false"
    >
      <div v-if="currentTask" class="task-progress">
        <el-progress
          :percentage="currentTask.progress"
          :status="currentTask.status === 'completed' ? 'success' : ''"
        />
        <div class="progress-stats">
          <span>总数: {{ currentTask.total }}</span>
          <span class="success">成功: {{ currentTask.success }}</span>
          <span class="failed">失败: {{ currentTask.failed }}</span>
        </div>
        <div class="progress-status">
          状态: {{ getStatusText(currentTask.status) }}
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, ArrowDown, ArrowUp, DataAnalysis } from '@element-plus/icons-vue'
import ProductList from './components/ProductList.vue'
import { sourcingApi } from '@/api/sourcing'
import { accountApi } from '@/api/account'

// 统计数据
const stats = ref([
  { key: 'total', value: 0, label: '已选商品' },
  { key: 'today', value: 0, label: '今日上架' },
  { key: 'published', value: 0, label: '已发布' },
  { key: 'profit', value: '¥0', label: '预估利润' },
])

// 搜索表单
const searchForm = reactive({
  keyword: '',
  sources: ['pdd', '1688'],
  minPrice: null,
  maxPrice: null,
  sort: 'default',
})

// 爆款筛选
const hotFilter = reactive({
  minMonthlySales: 100,
  minProfitMargin: 30,
  maxCompetition: 0.8,
  minRating: 4,
})

// 状态
const searchLoading = ref(false)
const analyzing = ref(false)
const showAdvancedFilter = ref(false)
const activeTab = ref('all')
const selectedProducts = ref([])

// 搜索结果
const searchResults = ref({ pdd: [], ali1688: [] })

const allProducts = computed(() => {
  return [...searchResults.value.pdd, ...searchResults.value.ali1688]
})

const pddProducts = computed(() => searchResults.value.pdd)
const ali1688Products = computed(() => searchResults.value.ali1688)
const totalCount = computed(() => allProducts.value.length)

// 批量发布
const batchPublishVisible = ref(false)
const publishing = ref(false)
const accounts = ref([])
const batchForm = reactive({
  name: '',
  targetAccounts: [],
  priceMarkup: 1.5,
  addWatermark: true,
  compressImages: true,
  removeDuplicates: true,
  optimizeTitle: true,
})

// 标题优化
const optimizeDialogVisible = ref(false)
const optimizing = ref(false)
const optimizeResult = ref(null)
const currentOptimizingProduct = ref(null)

// 任务进度
const taskProgressVisible = ref(false)
const currentTask = ref(null)

// 搜索商品
const handleSearch = async () => {
  if (!searchForm.keyword.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }

  searchLoading.value = true
  try {
    const res = await sourcingApi.searchProducts({
      keyword: searchForm.keyword,
      sources: searchForm.sources,
      min_price: searchForm.minPrice,
      max_price: searchForm.maxPrice,
      sort: searchForm.sort,
    })
    searchResults.value = {
      pdd: res.pdd || [],
      ali1688: res.ali1688 || [],
    }
    ElMessage.success(`找到 ${totalCount.value} 件商品`)
  } catch (error) {
    ElMessage.error('搜索失败')
  } finally {
    searchLoading.value = false
  }
}

// 获取爆款商品
const getHotProducts = async () => {
  searchLoading.value = true
  try {
    const res = await sourcingApi.getHotProducts({
      min_monthly_sales: hotFilter.minMonthlySales,
      min_profit_margin: hotFilter.minProfitMargin,
      max_competition: hotFilter.maxCompetition,
      min_rating: hotFilter.minRating,
      price_min: searchForm.minPrice || 10,
      price_max: searchForm.maxPrice || 500,
    })
    searchResults.value = {
      pdd: res.products.filter(p => p.source === 'pdd'),
      ali1688: res.products.filter(p => p.source === '1688'),
    }
    ElMessage.success(`找到 ${res.total} 个爆款商品`)
  } catch (error) {
    ElMessage.error('获取爆款失败')
  } finally {
    searchLoading.value = false
  }
}

// 重置筛选
const resetFilter = () => {
  hotFilter.minMonthlySales = 100
  hotFilter.minProfitMargin = 30
  hotFilter.maxCompetition = 0.8
  hotFilter.minRating = 4
}

// 选择商品
const handleSelect = (selection) => {
  selectedProducts.value = selection
}

// 添加到商品中心
const addToCenter = async (product) => {
  try {
    await sourcingApi.addToCenter({
      sourcing_product_id: product.id,
      price_markup: 1.5,
      add_watermark: true,
      optimize_title: true,
    })
    ElMessage.success('已添加到商品中心')
  } catch (error) {
    ElMessage.error('添加失败')
  }
}

// 优化标题
const optimizeTitle = async (product) => {
  currentOptimizingProduct.value = product
  optimizeDialogVisible.value = true
  optimizing.value = true
  optimizeResult.value = null

  try {
    const res = await sourcingApi.optimizeTitle({
      title: product.title,
      category: product.category,
    })
    optimizeResult.value = res
  } catch (error) {
    ElMessage.error('优化失败')
  } finally {
    optimizing.value = false
  }
}

// 应用优化后的标题
const applyOptimizedTitle = () => {
  if (currentOptimizingProduct.value && optimizeResult.value) {
    currentOptimizingProduct.value.title = optimizeResult.value.optimized_title
    optimizeDialogVisible.value = false
    ElMessage.success('标题已更新')
  }
}

// 打开批量发布对话框
const openBatchPublish = async () => {
  if (selectedProducts.value.length === 0) {
    ElMessage.warning('请先选择商品')
    return
  }

  try {
    const res = await accountApi.getList()
    accounts.value = res
  } catch (error) {
    ElMessage.error('加载账号失败')
    return
  }

  batchForm.name = `${searchForm.keyword || '商品'}批量发布`
  batchPublishVisible.value = true
}

// 确认批量发布
const confirmBatchPublish = async () => {
  if (!batchForm.name.trim()) {
    ElMessage.warning('请输入任务名称')
    return
  }
  if (batchForm.targetAccounts.length === 0) {
    ElMessage.warning('请选择目标账号')
    return
  }

  publishing.value = true
  try {
    const res = await sourcingApi.batchPublish({
      name: batchForm.name,
      sourcing_product_ids: selectedProducts.value.map(p => p.id),
      target_account_ids: batchForm.targetAccounts,
      price_markup: batchForm.priceMarkup,
      add_watermark: batchForm.addWatermark,
      optimize_title: batchForm.optimizeTitle,
    })

    batchPublishVisible.value = false
    ElMessage.success('发布任务已创建')

    currentTask.value = {
      id: res.task_id,
      progress: 0,
      total: selectedProducts.value.length * batchForm.targetAccounts.length,
      success: 0,
      failed: 0,
      status: 'pending',
    }
    taskProgressVisible.value = true

    startProgressPolling(res.task_id)
  } catch (error) {
    ElMessage.error('创建任务失败')
  } finally {
    publishing.value = false
  }
}

// 轮询任务进度
const startProgressPolling = (taskId) => {
  const timer = setInterval(async () => {
    try {
      const res = await sourcingApi.getTaskProgress(taskId)
      currentTask.value = {
        ...currentTask.value,
        progress: res.progress,
        total: res.total,
        success: res.success,
        failed: res.failed,
        status: res.status,
      }

      if (['completed', 'failed', 'cancelled'].includes(res.status)) {
        clearInterval(timer)
      }
    } catch (error) {
      clearInterval(timer)
    }
  }, 2000)
}

// 获取状态文本
const getStatusText = (status) => {
  const statusMap = {
    pending: '等待中',
    running: '执行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return statusMap[status] || status
}

// 分析商品
const analyzeProducts = async () => {
  analyzing.value = true
  try {
    await sourcingApi.analyzeProducts()
    ElMessage.success('分析完成')
    if (searchForm.keyword) {
      await handleSearch()
    }
  } catch (error) {
    ElMessage.error('分析失败')
  } finally {
    analyzing.value = false
  }
}

// 加载账号列表
const loadAccounts = async () => {
  try {
    const res = await accountApi.getList()
    accounts.value = res
  } catch (error) {
    console.error('加载账号失败', error)
  }
}

onMounted(() => {
  loadAccounts()
})
</script>

<style scoped>
.sourcing-center {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0 0 8px;
  font-size: 24px;
}

.subtitle {
  color: #909399;
  margin: 0;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
}

.stat-label {
  color: #909399;
  margin-top: 8px;
}

.search-card {
  margin-bottom: 20px;
}

.keyword-input {
  margin-bottom: 16px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.price-separator {
  color: #909399;
}

.advanced-filter {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.results-card {
  min-height: 400px;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.optimize-loading {
  text-align: center;
  padding: 20px;
}

.original-title,
.optimized-title {
  margin-bottom: 16px;
}

.original-title label,
.optimized-title label {
  font-weight: bold;
  color: #606266;
}

.original-title p {
  margin: 8px 0;
  padding: 8px;
  background: #f5f7fa;
  border-radius: 4px;
}

.optimize-score {
  margin-bottom: 16px;
}

.optimize-score span {
  margin-left: 8px;
  color: #409eff;
  font-weight: bold;
}

.optimize-keywords {
  margin-bottom: 16px;
}

.keyword-tag {
  margin-right: 8px;
  margin-bottom: 8px;
}

.optimize-improvements ul {
  margin: 8px 0;
  padding-left: 20px;
  color: #606266;
}

.task-progress .progress-stats {
  display: flex;
  justify-content: space-around;
  margin: 16px 0;
}

.task-progress .success {
  color: #67c23a;
}

.task-progress .failed {
  color: #f56c6c;
}

.progress-status {
  text-align: center;
  color: #909399;
}
</style>
