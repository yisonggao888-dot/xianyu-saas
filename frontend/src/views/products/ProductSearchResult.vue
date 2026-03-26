<template>
  <div class="search-result">
    <div v-if="products.length === 0" class="empty-state">
      <el-empty description="暂无搜索结果" />
    </div>

    <el-row :gutter="15" v-else>
      <el-col
        v-for="product in products"
        :key="product.source_id"
        :xs="24"
        :sm="12"
        :md="8"
        :lg="8"
        class="product-col"
      >
        <el-card class="product-card" shadow="hover">
          <div class="product-image">
            <el-image :src="product.main_image" fit="cover" />
            <div v-if="product.sales_count > 0" class="sales-badge">
              已拼 {{ formatSales(product.sales_count) }}
            </div>
          </div>

          <div class="product-content">
            <div class="product-title" :title="product.title">
              {{ product.title }}
            </div>

            <div class="shop-info">
              <span class="shop-name">{{ product.shop_name }}</span>
              <el-rate
                v-model="product.shop_rating"
                disabled
                show-score
                text-color="#ff9900"
                score-template="{value}"
              />
            </div>

            <div class="price-info">
              <div class="price-row">
                <span class="label">成本价:</span>
                <span class="cost">¥{{ product.price.toFixed(2) }}</span>
              </div>
              <div class="price-row">
                <span class="label">建议售价:</span>
                <span class="suggested">
                  ¥{{ product.profit_margin.suggested_price.toFixed(2) }}
                </span>
              </div>
              <div class="price-row profit">
                <span class="label">预估利润:</span>
                <span class="profit-amount">
                  ¥{{ product.profit_margin.profit.toFixed(2) }}
                  <small>({{ product.profit_margin.margin_percent }}%)</small>
                </span>
              </div>
            </div>
          </div>

          <template #footer>
            <el-button
              type="primary"
              @click="$emit('add-to-list', product)"
              :icon="Plus"
            >
              添加到选品
            </el-button>
            <el-button @click="viewDetail(product)">查看</el-button>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { Plus } from '@element-plus/icons-vue'

interface ProfitMargin {
  suggested_price: number
  profit: number
  margin_percent: number
}

interface Product {
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
  profit_margin: ProfitMargin
}

defineProps<{
  products: Product[]
}>()

defineEmits<{
  (e: 'add-to-list', product: Product): void
}>()

const formatSales = (count: number): string => {
  if (count >= 10000) {
    return (count / 10000).toFixed(1) + '万'
  }
  return count.toString()
}

const viewDetail = (product: Product) => {
  window.open(product.detail_url, '_blank')
}
</script>

<style scoped lang="scss">
.search-result {
  .product-col {
    margin-bottom: 15px;
  }

  .product-card {
    height: 100%;
    display: flex;
    flex-direction: column;

    :deep(.el-card__body) {
      flex: 1;
      display: flex;
      flex-direction: column;
      padding: 12px;
    }

    .product-image {
      position: relative;
      height: 180px;
      margin-bottom: 10px;

      .el-image {
        width: 100%;
        height: 100%;
        border-radius: 4px;
      }

      .sales-badge {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(transparent, rgba(0,0,0,0.6));
        color: white;
        padding: 20px 10px 5px;
        font-size: 12px;
      }
    }

    .product-content {
      flex: 1;

      .product-title {
        font-size: 14px;
        line-height: 1.4;
        height: 40px;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        margin-bottom: 8px;
      }

      .shop-info {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
        font-size: 12px;

        .shop-name {
          color: #606266;
          max-width: 100px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        :deep(.el-rate) {
          height: auto;

          .el-rate__icon {
            font-size: 12px;
            margin-right: 2px;
          }

          .el-rate__text {
            font-size: 12px;
          }
        }
      }

      .price-info {
        background: #f5f7fa;
        padding: 8px;
        border-radius: 4px;

        .price-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 12px;
          margin-bottom: 4px;

          &:last-child {
            margin-bottom: 0;
          }

          &.profit {
            .profit-amount {
              color: #67c23a;
              font-weight: bold;

              small {
                font-weight: normal;
                margin-left: 4px;
              }
            }
          }

          .label {
            color: #909399;
          }

          .cost {
            color: #f56c6c;
            text-decoration: line-through;
          }

          .suggested {
            color: #409eff;
            font-weight: bold;
          }
        }
      }
    }
  }
}
</style>
