<script setup lang="ts">
import { ref } from 'vue'

// 统计数据
const stats = ref([
  { title: '在线账号', value: 3, icon: 'UserFilled', color: '#409eff' },
  { title: '今日消息', value: 156, icon: 'ChatDotRound', color: '#67c23a' },
  { title: '待处理订单', value: 12, icon: 'List', color: '#e6a23c' },
  { title: '本月收益', value: '¥3,280', icon: 'Money', color: '#f56c6c' },
])

// 快捷操作
const quickActions = [
  { title: '添加闲鱼账号', icon: 'Plus', path: '/accounts' },
  { title: '查看对话', icon: 'ChatDotRound', path: '/conversations' },
  { title: '选品中心', icon: 'GoodsFilled', path: '/products' },
  { title: '系统设置', icon: 'Setting', path: '/settings' },
]

// 最近对话
const recentConversations = ref([
  { id: 1, buyer: '买家小王', message: '这个还能便宜吗？', time: '5分钟前', item: 'iPhone 14 Pro' },
  { id: 2, buyer: '数码达人', message: '支持验机吗？', time: '12分钟前', item: 'MacBook Air M2' },
  { id: 3, buyer: '宝妈一枚', message: '包邮吗？', time: '28分钟前', item: '儿童玩具套装' },
  { id: 4, buyer: '学生党', message: '学生有优惠吗？', time: '1小时前', item: 'iPad Air 5' },
])

const goTo = (path: string) => {
  // TODO: 路由跳转
}
</script>

<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20">
      <el-col :span="6" v-for="stat in stats" :key="stat.title">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" :style="{ backgroundColor: stat.color + '20', color: stat.color }">
              <el-icon :size="24"><component :is="stat.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-title">{{ stat.title }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 快捷操作 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="16">
        <el-card title="快捷操作">
          <div class="quick-actions">
            <div
              v-for="action in quickActions"
              :key="action.title"
              class="action-item"
              @click="goTo(action.path)"
            >
              <el-icon :size="24" class="action-icon"><component :is="action.icon" /></el-icon>
              <span>{{ action.title }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card title="套餐信息">
          <div class="plan-info">
            <div class="plan-name">标准版</div>
            <div class="plan-detail">
              <p>账号数: 3 / 5</p>
              <p>月消息数: 1,560 / 5,000</p>
              <p>到期时间: 2026-06-30</p>
            </div>
            <el-button type="primary" size="small" style="width: 100%; margin-top: 10px;">
              升级套餐
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 最近对话 -->
    <el-row style="margin-top: 20px;">
      <el-col :span="24">
        <el-card title="最近对话">
          <el-table :data="recentConversations" style="width: 100%">
            <el-table-column prop="buyer" label="买家" width="150" />
            <el-table-column prop="item" label="商品" width="200" />
            <el-table-column prop="message" label="最新消息" />
            <el-table-column prop="time" label="时间" width="120" />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button type="primary" size="small">回复</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.stat-card {
  border-radius: 8px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  line-height: 1.2;
}

.stat-title {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.action-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  background: #f5f7fa;
}

.action-item:hover {
  background: #ecf5ff;
  color: #409eff;
}

.action-icon {
  margin-bottom: 8px;
}

.plan-name {
  font-size: 20px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 16px;
}

.plan-detail p {
  margin: 8px 0;
  color: #606266;
  font-size: 14px;
}
</style>
