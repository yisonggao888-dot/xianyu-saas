<template>
  <div class="orders-page">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="4">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.total_orders }}</div>
          <div class="stat-label">总订单</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="stat-card warning">
          <div class="stat-value">{{ stats.pending_count }}</div>
          <div class="stat-label">待处理</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="stat-card success">
          <div class="stat-value">{{ stats.completed_count }}</div>
          <div class="stat-label">已完成</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="stat-card">
          <div class="stat-value">¥{{ stats.total_sales?.toFixed(2) }}</div>
          <div class="stat-label">总销售额</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="stat-card profit">
          <div class="stat-value">¥{{ stats.total_profit?.toFixed(2) }}</div>
          <div class="stat-label">总利润</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.avg_margin_percent }}%</div>
          <div class="stat-label">平均利润率</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势图 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="24">
        <el-card title="近7天趋势">
          <div ref="chartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 订单列表 -->
    <el-card class="order-list" v-loading="loading">
      <template #header>
        <div class="list-header">
          <span>订单列表</span>
          <div class="header-actions">
            <el-radio-group v-model="statusFilter" size="small" @change="handleFilterChange">
              <el-radio-button label="">全部</el-radio-button>
              <el-radio-button label="pending">待付款</el-radio-button>
              <el-radio-button label="paid">待发货</el-radio-button>
              <el-radio-button label="shipped">已发货</el-radio-button>
              <el-radio-button label="completed">已完成</el-radio-button>
            </el-radio-group>
            <el-button type="primary" size="small" @click="refreshData">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="filteredOrders" stripe>
        <el-table-column type="index" width="50" />
        <el-table-column label="商品" min-width="200">
          <template #default="{ row }">
            <div class="item-title" :title="row.item_title">{{ row.item_title }}</div>
            <div class="order-id">订单号: {{ row.xianyu_order_id }}</div>
          </template>
        </el-table-column>
        <el-table-column label="售价" width="100">
          <template #default="{ row }">
            <span class="sale-price">¥{{ row.sold_price.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="成本" width="100">
          <template #default="{ row }">
            <span class="cost-price">¥{{ row.cost_price.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="利润" width="100">
          <template #default="{ row }">
            <span class="profit-text">
              ¥{{ row.profit.toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="150">
          <template #default="{ row }">
            <div class="time-info">
              <div>{{ formatDate(row.created_at) }}</div>
              <div class="time-ago">{{ timeAgo(row.created_at) }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="货源" width="120">
          <template #default="{ row }">
            <div v-if="row.source_platform">
              <el-tag :type="row.source_platform === 'pdd' ? 'danger' : 'warning'" size="small">
                {{ row.source_platform === 'pdd' ? '拼多多' : '1688' }}
              </el-tag>
              <div class="source-order-id" v-if="row.source_order_id">
                {{ row.source_order_id.slice(0, 10) }}...
              </div>
            </div>
            <el-tag v-else type="info" size="small">未采购</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button size="small" @click="viewDetail(row)">详情</el-button>
              <el-button
                v-if="row.status === 'paid'"
                size="small"
                type="primary"
                @click="showShipDialog(row)"
              >
                发货
              </el-button>
              <el-button
                v-if="row.status === 'pending'"
                size="small"
                type="warning"
                @click="showPurchaseDialog(row)"
              >
                采购
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 发货对话框 -->
    <el-dialog v-model="showShip" title="填写物流信息" width="400px">
      <el-form :model="shipForm" label-width="80px">
        <el-form-item label="物流公司">
          <el-select v-model="shipForm.company" placeholder="选择物流公司">
            <el-option label="顺丰速运" value="sf" />
            <el-option label="中通快递" value="zt" />
            <el-option label="圆通速递" value="yt" />
            <el-option label="韵达快递" value="yd" />
            <el-option label="申通快递" value="st" />
            <el-option label="百世快递" value="bs" />
            <el-option label="邮政EMS" value="ems" />
          </el-select>
        </el-form-item>
        <el-form-item label="物流单号">
          <el-input v-model="shipForm.tracking_number" placeholder="输入物流单号" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showShip = false">取消</el-button>
        <el-button type="primary" @click="confirmShip" :loading="shipLoading">
          确认发货
        </el-button>
      </template>
    </el-dialog>

    <!-- 采购对话框 -->
    <el-dialog v-model="showPurchase" title="自动采购" width="600px">
      <el-form :model="purchaseForm" label-width="100px" v-if="currentOrder">
        <el-form-item label="商品">
          <div class="purchase-product">
            <div class="title">{{ currentOrder.item_title }}</div>
            <div class="price">闲鱼售价: ¥{{ currentOrder.sold_price }}</div>
          </div>
        </el-form-item>
        
        <el-form-item label="采购平台" required>
          <el-radio-group v-model="purchaseForm.source">
            <el-radio label="pdd">拼多多</el-radio>
            <el-radio label="1688">1688</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="商品链接" required>
          <el-input 
            v-model="purchaseForm.source_url" 
            placeholder="粘贴拼多多或1688商品链接"
          />
        </el-form-item>
        
        <el-form-item label="商品ID">
          <el-input 
            v-model="purchaseForm.source_id" 
            placeholder="可选，系统会自动提取"
          />
        </el-form-item>
        
        <el-form-item label="规格">
          <el-input 
            v-model="purchaseForm.sku_spec" 
            placeholder="如：颜色/尺码等"
          />
        </el-form-item>
        
        <el-form-item label="数量">
          <el-input-number v-model="purchaseForm.quantity" :min="1" :max="99" />
        </el-form-item>
        
        <el-divider />
        
        <el-form-item label="收货人" required>
          <el-input v-model="purchaseForm.buyer_name" placeholder="买家姓名" />
        </el-form-item>
        
        <el-form-item label="手机号" required>
          <el-input v-model="purchaseForm.buyer_phone" placeholder="11位手机号" maxlength="11" />
        </el-form-item>
        
        <el-form-item label="收货地址" required>
          <el-input 
            v-model="purchaseForm.buyer_address" 
            type="textarea" 
            :rows="2"
            placeholder="详细收货地址"
          />
        </el-form-item>
      </el-form>
      
      <el-alert
        title="自动采购说明"
        type="info"
        description="系统将自动到货源平台下单，下单后需要您在拼多多/1688完成支付。"
        show-icon
        :closable="false"
        style="margin-top: 15px;"
      />
      
      <template #footer>
        <el-button @click="showPurchase = false">取消</el-button>
        <el-button type="primary" @click="confirmPurchase" :loading="purchaseLoading">
          提交采购任务
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getOrderList, getOrderStats, getDailyStats, updateOrderStatus } from '@/api/order'
import { createPurchase, getPurchaseTask } from '@/api/purchase'

interface Order {
  id: string
  conversation_id: string
  xianyu_order_id: string
  buyer_id: string
  item_title: string
  sold_price: number
  cost_price: number
  profit: number
  status: string
  source_platform: string | null
  source_order_id: string | null
  tracking_number: string | null
  created_at: string
  paid_at: string | null
  shipped_at: string | null
  completed_at: string | null
}

interface Stats {
  total_orders: number
  pending_count: number
  completed_count: number
  total_sales: number
  total_profit: number
  avg_margin_percent: number
  status_distribution: Record<string, number>
}

// 状态
const loading = ref(false)
const orders = ref<Order[]>([])
const stats = ref<Stats>({
  total_orders: 0,
  pending_count: 0,
  completed_count: 0,
  total_sales: 0,
  total_profit: 0,
  avg_margin_percent: 0,
  status_distribution: {},
})
const statusFilter = ref('')
const dailyStats = ref<any[]>([])

// 发货对话框
const showShip = ref(false)
const shipLoading = ref(false)
const currentOrder = ref<Order | null>(null)
const shipForm = ref({
  company: '',
  tracking_number: '',
})

// 采购对话框
const showPurchase = ref(false)
const purchaseLoading = ref(false)
const purchaseForm = ref({
  source: 'pdd',
  source_id: '',
  source_url: '',
  sku_spec: '',
  quantity: 1,
  buyer_name: '',
  buyer_phone: '',
  buyer_address: '',
})

// 图表
const chartRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

// 计算属性
const filteredOrders = computed(() => {
  if (!statusFilter.value) return orders.value
  return orders.value.filter(o => o.status === statusFilter.value)
})

// 方法
const fetchData = async () => {
  loading.value = true
  try {
    const [ordersRes, statsRes, dailyRes] = await Promise.all([
      getOrderList(),
      getOrderStats(30),
      getDailyStats(7),
    ])
    orders.value = ordersRes.data
    stats.value = statsRes.data
    dailyStats.value = dailyRes.data
    initChart()
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  fetchData()
  ElMessage.success('刷新成功')
}

const handleFilterChange = () => {
  // 筛选已在计算属性中处理
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'info',
    paid: 'warning',
    shipped: 'primary',
    completed: 'success',
    cancelled: 'danger',
  }
  return map[status] || 'info'
}

const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    pending: '待付款',
    paid: '待发货',
    shipped: '已发货',
    completed: '已完成',
    cancelled: '已取消',
  }
  return map[status] || status
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString()
}

const timeAgo = (dateStr: string) => {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
  
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  return `${Math.floor(diff / 86400)}天前`
}

const viewDetail = (_order: Order) => {
  ElMessage.info('详情功能开发中...')
}

const showShipDialog = (order: Order) => {
  currentOrder.value = order
  shipForm.value = { company: '', tracking_number: '' }
  showShip.value = true
}

const confirmShip = async () => {
  if (!shipForm.value.tracking_number) {
    ElMessage.warning('请输入物流单号')
    return
  }
  
  shipLoading.value = true
  try {
    await updateOrderStatus(currentOrder.value!.id, {
      status: 'shipped',
      tracking_number: shipForm.value.tracking_number,
    })
    ElMessage.success('发货成功')
    showShip.value = false
    fetchData()
  } finally {
    shipLoading.value = false
  }
}

const showPurchaseDialog = (order: Order) => {
  currentOrder.value = order
  purchaseForm.value = {
    source: 'pdd',
    source_id: '',
    source_url: '',
    sku_spec: '',
    quantity: 1,
    buyer_name: '',
    buyer_phone: '',
    buyer_address: '',
  }
  showPurchase.value = true
}

const confirmPurchase = async () => {
  if (!currentOrder.value) return
  
  if (!purchaseForm.value.source_url) {
    ElMessage.warning('请输入商品链接')
    return
  }
  if (!purchaseForm.value.buyer_name || !purchaseForm.value.buyer_phone || !purchaseForm.value.buyer_address) {
    ElMessage.warning('请填写完整的收货信息')
    return
  }
  
  purchaseLoading.value = true
  try {
    const res = await createPurchase({
      order_id: currentOrder.value.id,
      source: purchaseForm.value.source,
      source_id: purchaseForm.value.source_id,
      source_url: purchaseForm.value.source_url,
      sku_spec: purchaseForm.value.sku_spec || undefined,
      quantity: purchaseForm.value.quantity,
      buyer_name: purchaseForm.value.buyer_name,
      buyer_phone: purchaseForm.value.buyer_phone,
      buyer_address: purchaseForm.value.buyer_address,
    })
    
    ElMessage.success('采购任务已提交')
    showPurchase.value = false
    
    // 轮询任务状态
    pollTaskStatus(res.data.task_id)
  } finally {
    purchaseLoading.value = false
  }
}

const pollTaskStatus = async (taskId: string) => {
  const checkStatus = async () => {
    try {
      const res = await getPurchaseTask(taskId)
      const task = res.data
      
      if (task.status === 'success') {
        ElMessage.success(`采购成功！货源订单号: ${task.result?.order_id}`)
        fetchData() // 刷新数据
        return
      } else if (task.status === 'failed') {
        ElMessage.error(`采购失败: ${task.error_msg}`)
        return
      }
      
      // 继续轮询
      setTimeout(checkStatus, 3000)
    } catch (e) {
      console.error('轮询失败', e)
    }
  }
  
  checkStatus()
}

const initChart = () => {
  if (!chartRef.value || dailyStats.value.length === 0) return
  
  if (chart) {
    chart.dispose()
  }
  
  chart = echarts.init(chartRef.value)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    legend: {
      data: ['订单数', '销售额', '利润'],
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dailyStats.value.map(d => d.date.slice(5)),
    },
    yAxis: [
      {
        type: 'value',
        name: '订单数',
        position: 'left',
      },
      {
        type: 'value',
        name: '金额',
        position: 'right',
        axisLabel: {
          formatter: '¥{value}',
        },
      },
    ],
    series: [
      {
        name: '订单数',
        type: 'line',
        data: dailyStats.value.map(d => d.orders),
        smooth: true,
      },
      {
        name: '销售额',
        type: 'line',
        yAxisIndex: 1,
        data: dailyStats.value.map(d => d.sales),
        smooth: true,
      },
      {
        name: '利润',
        type: 'line',
        yAxisIndex: 1,
        data: dailyStats.value.map(d => d.profit),
        smooth: true,
      },
    ],
  }
  
  chart.setOption(option)
}

// 监听窗口大小变化
const handleResize = () => {
  chart?.resize()
}

// 初始化
onMounted(() => {
  fetchData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style scoped lang="scss">
.orders-page {
  .stats-row {
    margin-bottom: 20px;

    .stat-card {
      text-align: center;

      &.warning .stat-value {
        color: #e6a23c;
      }

      &.success .stat-value {
        color: #67c23a;
      }

      &.profit .stat-value {
        color: #409eff;
      }

      .stat-value {
        font-size: 24px;
        font-weight: bold;
        color: #606266;
      }

      .stat-label {
        font-size: 12px;
        color: #909399;
        margin-top: 5px;
      }
    }
  }

  .chart-row {
    margin-bottom: 20px;

    .chart-container {
      height: 300px;
    }
  }

  .order-list {
    .list-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .header-actions {
        display: flex;
        gap: 15px;
      }
    }

    .item-title {
      font-size: 14px;
      line-height: 1.4;
      max-width: 180px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .order-id {
      font-size: 12px;
      color: #909399;
      margin-top: 4px;
    }

    .sale-price {
      color: #f56c6c;
      font-weight: bold;
    }

    .cost-price {
      color: #909399;
    }

    .profit-text {
      color: #67c23a;
      font-weight: bold;
    }

    .time-info {
      .time-ago {
        font-size: 12px;
        color: #909399;
        margin-top: 4px;
      }
    }

    .source-order-id {
      font-size: 12px;
      color: #909399;
      margin-top: 4px;
    }
  }

  .purchase-product {
    padding: 10px;
    background: #f5f7fa;
    border-radius: 4px;

    .title {
      font-size: 14px;
      margin-bottom: 5px;
    }

    .price {
      color: #f56c6c;
      font-weight: bold;
    }
  }
}
</style>
