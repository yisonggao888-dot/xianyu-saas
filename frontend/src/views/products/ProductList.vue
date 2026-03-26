<template>
  <div class="products-page">
    <div class="page-header">
      <h2>选品中心</h2>
      <el-button type="primary" @click="showSearchDialog = true">
        <el-icon><Search /></el-icon>
        搜索货源
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="4">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.total_products }}</div>
          <div class="stat-label">选品总数</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.active_products }}</div>
          <div class="stat-label">已上架</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.total_orders }}</div>
          <div class="stat-label">已售订单</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="stat-card">
          <div class="stat-value">¥{{ stats.total_sales.toFixed(2) }}</div>
          <div class="stat-label">总销售额</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="stat-card profit">
          <div class="stat-value">¥{{ stats.total_profit.toFixed(2) }}</div>
          <div class="stat-label">总利润</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 选品列表 -->
    <el-card class="product-list">
      <template #header>
        <div class="list-header">
          <span>我的选品</span>
          <el-radio-group v-model="listFilter" size="small">
            <el-radio-button label="all">全部</el-radio-button>
            <el-radio-button label="active">已上架</el-radio-button>
            <el-radio-button label="inactive">已下架</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-table :data="filteredProducts" v-loading="loading">
        <el-table-column type="index" width="50" />
        <el-table-column label="商品" min-width="250">
          <template #default="{ row }">
            <div class="product-info">
              <el-image :src="row.main_image" class="product-thumb" fit="cover" />
              <div class="product-detail">
                <div class="product-title">{{ row.title }}</div>
                <el-tag size="small" :type="row.source === 'pdd' ? 'danger' : 'warning'">
                  {{ row.source === 'pdd' ? '拼多多' : '1688' }}
                </el-tag>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="成本价" width="100">
          <template #default="{ row }">
            <span class="cost-price">¥{{ row.cost_price.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="售价" width="100">
          <template #default="{ row }">
            <span class="sale-price">¥{{ row.sale_price.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="利润" width="100">
          <template #default="{ row }">
            <span class="profit-text">
              ¥{{ row.profit.toFixed(2) }}
              <small>({{ row.profit_margin }}%)</small>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '已上架' : '已下架' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button size="small" @click="viewDetail(row)">详情</el-button>
              <el-button size="small" type="primary" @click="publishToXianyu(row)">
                发布
              </el-button>
              <el-button size="small" type="danger" @click="deleteProduct(row.id)">
                删除
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 搜索对话框 -->
    <el-dialog
      v-model="showSearchDialog"
      title="搜索货源"
      width="900px"
      destroy-on-close
    >
      <el-form :model="searchForm" inline>
        <el-form-item label="关键词">
          <el-input
            v-model="searchForm.keyword"
            placeholder="输入商品关键词"
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button @click="handleSearch">搜索</el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="平台">
          <el-checkbox-group v-model="searchForm.sources">
            <el-checkbox label="pdd">拼多多</el-checkbox>
            <el-checkbox label="1688">1688</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="价格区间">
          <el-input-number v-model="searchForm.min_price" :min="0" :precision="2" placeholder="最低价" />
          <span class="price-separator">-</span>
          <el-input-number v-model="searchForm.max_price" :min="0" :precision="2" placeholder="最高价" />
        </el-form-item>
        <el-form-item label="最低销量">
          <el-input-number v-model="searchForm.min_sales" :min="0" placeholder="销量" />
        </el-form-item>
      </el-form>

      <el-tabs v-model="activeTab" v-loading="searchLoading">
        <el-tab-pane label="拼多多" name="pdd">
          <ProductSearchResult
            :products="searchResults.pdd"
            @add-to-list="handleAddToList"
          />
        </el-tab-pane>
        <el-tab-pane label="1688" name="ali1688">
          <ProductSearchResult
            :products="searchResults.ali1688"
            @add-to-list="handleAddToList"
          />
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <!-- 添加选品对话框 -->
    <el-dialog v-model="showAddDialog" title="添加选品" width="500px">
      <el-form :model="addForm" label-width="80px">
        <el-form-item label="商品">
          <div class="add-product-preview">
            <el-image :src="addForm.main_image" class="preview-img" />
            <div class="preview-title">{{ addForm.title }}</div>
          </div>
        </el-form-item>
        <el-form-item label="成本价">
          <el-input-number v-model="addForm.cost_price" :precision="2" disabled />
        </el-form-item>
        <el-form-item label="建议售价">
          <el-input-number
            v-model="addForm.sale_price"
            :precision="2"
            :min="addForm.cost_price"
          />
          <span class="profit-preview">
            利润: ¥{{ (addForm.sale_price - addForm.cost_price).toFixed(2) }}
            ({{ ((addForm.sale_price - addForm.cost_price) / addForm.cost_price * 100).toFixed(1) }}%)
          </span>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="addForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmAdd" :loading="addLoading">
          添加到选品
        </el-button>
      </template>
    </el-dialog>

    <!-- 发布到闲鱼对话框 -->
    <el-dialog v-model="showPublishDialog" title="发布到闲鱼" width="500px">
      <el-form :model="publishForm" label-width="100px" v-if="currentProduct">
        <el-form-item label="商品">
          <div class="publish-product-preview">
            <el-image :src="currentProduct.main_image" class="preview-img" />
            <div class="preview-info">
              <div class="title">{{ currentProduct.title }}</div>
              <div class="price">成本: ¥{{ currentProduct.cost_price }} / 售价: ¥{{ currentProduct.sale_price }}</div>
            </div>
          </div>
        </el-form-item>
        
        <el-form-item label="发布账号" required>
          <el-select v-model="publishForm.account_id" placeholder="选择闲鱼账号" style="width: 100%">
            <el-option
              v-for="acc in accounts"
              :key="acc.id"
              :label="acc.name"
              :value="acc.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="售价">
          <el-input-number v-model="publishForm.sale_price" :precision="2" :min="0" style="width: 100%" />
        </el-form-item>
      </el-form>
      
      <el-alert
        title="发布说明"
        type="info"
        description="系统将自动打开发布页面，您需要手动完成图片上传和最终确认。"
        show-icon
        :closable="false"
        style="margin-top: 15px;"
      />
      
      <template #footer>
        <el-button @click="showPublishDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmPublish" :loading="publishLoading">
          开始发布
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import ProductSearchResult from './ProductSearchResult.vue'
import { searchProducts, getProductList, addToList, deleteProduct as deleteProductApi, getProductStats } from '@/api/product'
import { publishToXianyu } from '@/api/publish'
import { getAccountList } from '@/api/account'

interface Product {
  id: string
  source: string
  source_id: string
  title: string
  cost_price: number
  sale_price: number
  profit: number
  profit_margin: number
  main_image: string
  detail_url: string
  description?: string
  status: string
}

interface SearchResult {
  source: string
  source_id: string
  title: string
  price: number
  original_price?: number
  main_image: string
  sales_count: number
  shop_name: string
  shop_rating: number
  detail_url: string
  category?: string
  profit_margin: {
    suggested_price: number
    profit: number
    margin_percent: number
  }
}

// 状态
const loading = ref(false)
const searchLoading = ref(false)
const addLoading = ref(false)
const listFilter = ref('all')
const showSearchDialog = ref(false)
const showAddDialog = ref(false)
const activeTab = ref('pdd')
const products = ref<Product[]>([])
const searchResults = ref<{ pdd: SearchResult[], ali1688: SearchResult[] }>({ pdd: [], ali1688: [] })
const stats = ref({
  total_products: 0,
  active_products: 0,
  total_orders: 0,
  total_sales: 0,
  total_profit: 0,
})

// 搜索表单
const searchForm = ref({
  keyword: '',
  sources: ['pdd', '1688'] as string[],
  min_price: undefined as number | undefined,
  max_price: undefined as number | undefined,
  min_sales: undefined as number | undefined,
})

// 添加表单
const addForm = ref({
  source: '',
  source_id: '',
  title: '',
  cost_price: 0,
  sale_price: 0,
  main_image: '',
  detail_url: '',
  description: '',
})

// 发布对话框
const showPublishDialog = ref(false)
const publishLoading = ref(false)
const currentProduct = ref<Product | null>(null)
const accounts = ref<{id: string, name: string}[]>([])
const publishForm = ref({
  product_id: '',
  account_id: '',
  sale_price: 0,
})

// 计算属性
const filteredProducts = computed(() => {
  if (listFilter.value === 'all') return products.value
  return products.value.filter(p => p.status === listFilter.value)
})

// 方法
const fetchProducts = async () => {
  loading.value = true
  try {
    const res = await getProductList()
    products.value = res.data
  } finally {
    loading.value = false
  }
}

const fetchStats = async () => {
  try {
    const res = await getProductStats()
    stats.value = res.data
  } catch (e) {
    console.error('获取统计失败', e)
  }
}

const handleSearch = async () => {
  if (!searchForm.value.keyword) {
    ElMessage.warning('请输入关键词')
    return
  }

  searchLoading.value = true
  try {
    const res = await searchProducts({
      keyword: searchForm.value.keyword,
      sources: searchForm.value.sources,
      min_price: searchForm.value.min_price,
      max_price: searchForm.value.max_price,
      min_sales: searchForm.value.min_sales,
    })
    searchResults.value = res.data
  } finally {
    searchLoading.value = false
  }
}

const handleAddToList = (product: SearchResult) => {
  addForm.value = {
    source: product.source,
    source_id: product.source_id,
    title: product.title,
    cost_price: product.price,
    sale_price: product.profit_margin.suggested_price,
    main_image: product.main_image,
    detail_url: product.detail_url,
    description: '',
  }
  showAddDialog.value = true
}

const confirmAdd = async () => {
  addLoading.value = true
  try {
    await addToList(addForm.value)
    ElMessage.success('添加成功')
    showAddDialog.value = false
    fetchProducts()
    fetchStats()
  } finally {
    addLoading.value = false
  }
}

const deleteProduct = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定要删除这个商品吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteProductApi(id)
    ElMessage.success('删除成功')
    fetchProducts()
    fetchStats()
  } catch (e) {
    // 用户取消
  }
}

const viewDetail = (product: Product) => {
  window.open(product.detail_url, '_blank')
}

const publishToXianyu = (product: Product) => {
  currentProduct.value = product
  publishForm.value = {
    product_id: product.id,
    account_id: '',
    sale_price: product.sale_price,
  }
  fetchAccounts()
  showPublishDialog.value = true
}

const fetchAccounts = async () => {
  try {
    const res = await getAccountList()
    accounts.value = res.data.map((a: any) => ({
      id: a.id,
      name: a.name,
    }))
  } catch (e) {
    console.error('获取账号失败', e)
  }
}

const confirmPublish = async () => {
  if (!publishForm.value.account_id) {
    ElMessage.warning('请选择发布账号')
    return
  }
  
  publishLoading.value = true
  try {
    const res = await publishToXianyu({
      product_id: publishForm.value.product_id,
      account_id: publishForm.value.account_id,
      sale_price: publishForm.value.sale_price,
    })
    
    if (res.data.success) {
      ElMessage.success('发布成功！')
      showPublishDialog.value = false
      fetchProducts()
    } else {
      ElMessage.error(res.data.error || '发布失败')
    }
  } finally {
    publishLoading.value = false
  }
}

// 初始化
onMounted(() => {
  fetchProducts()
  fetchStats()
})
</script>

<style scoped lang="scss">
.products-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    h2 {
      margin: 0;
    }
  }

  .stats-row {
    margin-bottom: 20px;

    .stat-card {
      text-align: center;

      &.profit {
        .stat-value {
          color: #67c23a;
        }
      }

      .stat-value {
        font-size: 24px;
        font-weight: bold;
        color: #409eff;
      }

      .stat-label {
        font-size: 12px;
        color: #909399;
        margin-top: 5px;
      }
    }
  }

  .product-list {
    .list-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .product-info {
      display: flex;
      align-items: center;
      gap: 10px;

      .product-thumb {
        width: 60px;
        height: 60px;
        border-radius: 4px;
      }

      .product-detail {
        .product-title {
          font-size: 14px;
          margin-bottom: 5px;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      }
    }

    .cost-price {
      color: #909399;
      text-decoration: line-through;
    }

    .sale-price {
      color: #f56c6c;
      font-weight: bold;
    }

    .profit-text {
      color: #67c23a;

      small {
        color: #909399;
      }
    }
  }

  .price-separator {
    margin: 0 10px;
    color: #909399;
  }

  .add-product-preview {
    display: flex;
    align-items: center;
    gap: 10px;

    .preview-img {
      width: 80px;
      height: 80px;
      border-radius: 4px;
    }

    .preview-title {
      flex: 1;
      font-size: 14px;
    }
  }

  .profit-preview {
    margin-left: 10px;
    color: #67c23a;
  }

  .publish-product-preview {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px;
    background: #f5f7fa;
    border-radius: 4px;

    .preview-img {
      width: 80px;
      height: 80px;
      border-radius: 4px;
    }

    .preview-info {
      flex: 1;

      .title {
        font-size: 14px;
        margin-bottom: 5px;
      }

      .price {
        font-size: 12px;
        color: #909399;
      }
    }
  }
}
</style>
