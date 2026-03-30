<template>
  <div class="product-list">
    <el-empty v-if="!loading && products.length === 0" description="暂无商品数据" />
    
    <el-table
      v-else
      :data="products"
      v-loading="loading"
      @selection-change="handleSelectionChange"
      style="width: 100%"
    >
      <el-table-column type="selection" width="55" />
      
      <el-table-column label="商品" min-width="300">
        <template #default="{ row }">
          <div class="product-info">
            <el-image
              :src="row.main_image"
              :preview-src-list="[row.main_image]"
              fit="cover"
              class="product-image"
            />
            <div class="product-detail">
              <div class="product-title" :title="row.title">{{ row.title }}</div>
              <div class="product-meta">
                <el-tag size="small" :type="row.source === 'pdd' ? 'danger' : 'primary'">
                  {{ row.source === 'pdd' ? '拼多多' : '1688' }}
                </el-tag>
                <span class="shop-name">{{ row.shop_name }}</span>
              </div>
              <div class="product-category" v-if="row.category">
                分类: {{ row.category }}
              </div>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="价格" width="150">
        <template #default="{ row }">
          <div class="price-info">
            <div class="cost-price">成本: ¥{{ row.price }}</div>
            <div class="suggested-price" v-if="row.profit_margin">
              建议售价: ¥{{ row.profit_margin.suggested_price }}
            </div>
            <div class="profit" v-if="row.profit_margin">
              利润: ¥{{ row.profit_margin.profit }}
              <el-tag size="small" type="success">{{ row.profit_margin.margin_percent }}%</el-tag>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="销量数据" width="150">
        <template #default="{ row }">
          <div class="sales-info">
            <div class="monthly-sales">月销: {{ formatSales(row.sales_count || row.monthly_sales) }}</div>
            <div class="total-sales" v-if="row.total_sales">
              总销: {{ formatSales(row.total_sales) }}
            </div>
            <div class="rating" v-if="row.rating || row.shop_rating">
              <el-rate
                :model-value="row.rating || row.shop_rating"
                disabled
                :max="5"
                size="small"
              />
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="分析指标" width="180" v-if="showAnalysis">
        <template #default="{ row }">
          <div class="analysis-info">
            <div class="score-item">
              <span>热度:</span>
              <el-progress
                :percentage="row.hot_score || 0"
                :color="getScoreColor(row.hot_score)"
                :stroke-width="8"
              />
            </div>
            <div class="score-item">
              <span>盈利:</span>
              <el-progress
                :percentage="row.profit_score || 0"
                :color="getScoreColor(row.profit_score)"
                :stroke-width="8"
              />
            </div>
            <div class="score-item">
              <span>竞争:</span>
              <el-progress
                :percentage="row.competition_score || 0"
                :color="getCompetitionColor(row.competition_score)"
                :stroke-width="8"
              />
            </div>
            <div class="comprehensive-score" v-if="row.comprehensive_score">
              综合: <el-tag :type="getScoreTagType(row.comprehensive_score)">{{ row.comprehensive_score }}分</el-tag>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <div class="action-buttons">
            <el-button
              type="primary"
              size="small"
              @click="$emit('add-to-center', row)"
            >
              一键上架
            </el-button>
            <el-button
              type="info"
              size="small"
              @click="$emit('optimize-title', row)"
            >
              AI优化
            </el-button>
            <el-button
              link
              size="small"
              @click="openSourceUrl(row)"
            >
              查看源站
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  products: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['select', 'add-to-center', 'optimize-title'])

// 是否显示分析列
const showAnalysis = computed(() => {
  return props.products.some(p => p.hot_score !== undefined)
})

// 选择变化
const handleSelectionChange = (selection) => {
  emit('select', selection)
}

// 格式化销量
const formatSales = (sales) => {
  if (!sales) return '0'
  if (sales >= 10000) {
    return (sales / 10000).toFixed(1) + '万'
  }
  return sales.toString()
}

// 获取分数颜色
const getScoreColor = (score) => {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#e6a23c'
  return '#f56c6c'
}

// 获取竞争分数颜色（竞争越小越好）
const getCompetitionColor = (score) => {
  if (score >= 60) return '#67c23a'
  if (score >= 40) return '#e6a23c'
  return '#f56c6c'
}

// 获取分数标签类型
const getScoreTagType = (score) => {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

// 打开源站链接
const openSourceUrl = (row) => {
  if (row.detail_url || row.source_url) {
    window.open(row.detail_url || row.source_url, '_blank')
  }
}
</script>

<style scoped>
.product-list {
  width: 100%;
}

.product-info {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.product-image {
  width: 80px;
  height: 80px;
  border-radius: 4px;
  flex-shrink: 0;
}

.product-detail {
  flex: 1;
  min-width: 0;
}

.product-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  line-height: 1.4;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.shop-name {
  font-size: 12px;
  color: #909399;
}

.product-category {
  font-size: 12px;
  color: #606266;
}

.price-info {
  line-height: 1.8;
}

.cost-price {
  color: #f56c6c;
  font-weight: 500;
}

.suggested-price {
  color: #67c23a;
}

.profit {
  color: #e6a23c;
  display: flex;
  align-items: center;
  gap: 4px;
}

.sales-info {
  line-height: 1.8;
}

.monthly-sales {
  color: #409eff;
  font-weight: 500;
}

.total-sales {
  color: #909399;
  font-size: 12px;
}

.analysis-info .score-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  gap: 8px;
}

.analysis-info .score-item span {
  font-size: 12px;
  color: #606266;
  width: 40px;
}

.analysis-info .comprehensive-score {
  margin-top: 8px;
  font-size: 13px;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-buttons .el-button {
  margin: 0;
}
</style>
