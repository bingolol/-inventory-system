<template>
  <div>
    <div style="margin-bottom:8px;font-weight:600;">{{ title }}</div>
    <el-table :data="items" size="small" :border="true" style="width:100%">
      <el-table-column label="商品" min-width="160">
        <template #default="{ row, $index }">
          <el-select v-model="row.product_id" filterable placeholder="选择商品" size="small" style="width:100%" @change="onProductChange($index)">
            <el-option v-for="p in products" :key="p.id" :label="productLabel(p)" :value="p.id" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="数量" width="100">
        <template #default="{ row }">
          <el-input-number v-model="row.quantity" :min="1" size="small" style="width:90px" />
        </template>
      </el-table-column>
      <el-table-column label="单价" width="120">
        <template #default="{ row }">
          <el-input-number v-model="row.unit_price" :min="0" :precision="2" size="small" style="width:110px" />
        </template>
      </el-table-column>
      <el-table-column label="小计" width="100">
        <template #default="{ row }">¥{{ formatMoney(row.quantity * row.unit_price) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="60">
        <template #default="{ $index }">
          <el-button size="small" link type="danger" @click="removeItem($index)"><el-icon><Delete /></el-icon></el-button>
        </template>
      </el-table-column>
    </el-table>
    <div style="margin-top:8px;">
      <el-button size="small" @click="addItem"><el-icon><Plus /></el-icon> 添加商品</el-button>
      <template v-if="showCustomPrice">
        <div style="float:right;display:flex;align-items:center;gap:8px;">
          <span class="subtotal-label">明细合计: ¥{{ formatMoney(orderTotal) }}</span>
          <span class="subtotal-arrow">→</span>
          <el-input-number v-model="totalPriceModel" :precision="2" :min="0" size="small" placeholder="自定义金额" style="width:130px;" />
          <span class="total-amount">订单总额: ¥{{ formatMoney(totalPriceModel ?? orderTotal) }}</span>
        </div>
      </template>
      <template v-else>
        <span class="total-amount" style="float:right;">订单总额: ¥{{ formatMoney(orderTotal) }}</span>
      </template>
    </div>
  </div>
</template>

<script setup>
import { Delete, Plus } from '@element-plus/icons-vue'
import { formatMoney } from '../api/common'

const props = defineProps({
  /** 明细行数组（引用类型，直接操作） */
  items: { type: Array, required: true },
  /** 商品列表 */
  products: { type: Array, default: () => [] },
  /** 商品选项是否显示库存（销售=true，采购=false） */
  showStock: { type: Boolean, default: false },
  /** 是否显示自定义金额输入（销售=true，采购=false） */
  showCustomPrice: { type: Boolean, default: false },
  /** 明细合计（由父组件 computed 传入） */
  orderTotal: { type: Number, default: 0 },
  /** 标题文字 */
  title: { type: String, default: '订单明细' }
})

const emit = defineEmits(['product-change'])

// totalPrice 双向绑定
const totalPriceModel = defineModel('totalPrice', { type: Number, default: null })

/** 商品选项 label */
const productLabel = (p) => {
  const base = `${p.name} (${p.sku})`
  return props.showStock ? `${base} 库存:${p.current_stock ?? 0}` : base
}

/** 添加空行 */
const addItem = () => {
  props.items.push({ product_id: null, quantity: 1, unit_price: 0 })
}

/** 删除行 */
const removeItem = (idx) => {
  props.items.splice(idx, 1)
}

/** 商品选择变化 — 通知父组件处理防重+自动填充 */
const onProductChange = (idx) => {
  emit('product-change', idx)
}
</script>

<style scoped>
.subtotal-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}
.subtotal-arrow {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}
.total-amount {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-color-primary);
}
</style>