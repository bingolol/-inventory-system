<template>
  <el-dialog :model-value="visible" @update:model-value="$emit('update:visible', $event)" :title="isEdit?'编辑销售单':'新建销售单'" width="680px" destroy-on-close>
    <el-form label-width="80px">
      <el-form-item label="客户"><el-select v-model="form.customer_name" filterable allow-create default-first-option clearable placeholder="选择或输入客户名(可空=散客)" style="width:100%"><el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.name" /></el-select></el-form-item>
<el-form-item v-if="!isEdit" label="税率"><el-select v-model="form.tax_rate" style="width:100%"><el-option label="0%" :value="0" /><el-option label="3%" :value="0.03" /><el-option label="6%" :value="0.06" /><el-option label="9%" :value="0.09" /><el-option label="13%" :value="0.13" /></el-select></el-form-item>
      <el-form-item label="是否开票"><el-switch v-model="form.has_invoice" /></el-form-item>
      <el-form-item label="支付状态">
        <el-select v-model="form.payment_status" style="width:100%">
          <template v-if="!isEdit"><el-option v-for="opt in enumsStore.paymentStatusOptions" :key="opt.value" :label="opt.label" :value="opt.value" /></template>
          <template v-else><el-option label="未支付" value="unpaid" /><el-option label="已支付" value="paid" /></template>
        </el-select>
      </el-form-item>
      <el-form-item label="备注"><el-input v-model="form.notes" type="textarea" :rows="2" /></el-form-item>
      <el-form-item label="附件图片"><ImageUpload v-model="form.image_url" business-type="sale" :record-id="form.id||0" :update-api="data => ordersApi.updateSale(form.id, data)" /></el-form-item>
    </el-form>
    <OrderItemEditor :items="form.items" :products="products" show-stock show-custom-price :order-total="orderTotal" v-model:total-price="form.total_price" :title="isEdit?'销售明细（修改后保存将重新计算库存/收入）':'销售明细'" @product-change="onProductChange" />
    <div v-if="isEdit && form.items.length===0" style="margin-top:8px;color:var(--el-color-danger);font-size:12px"><el-icon><Warning /></el-icon> 删除所有商品后保存将自动删除此销售单</div>
    
    <!-- 操作反馈 -->
    <el-alert 
      v-if="operationFeedback && operationFeedback.show" 
      :type="operationFeedback.type" 
      :title="operationFeedback.message" 
      :closable="false"
      style="margin-top: 12px"
    >
      <div v-if="operationFeedback.details && operationFeedback.details.length > 0" style="margin-top: 8px; font-size: 12px;">
        <div v-for="(detail, idx) in operationFeedback.details" :key="idx">
          {{ detail.label }}: <b>{{ detail.value }}</b>
        </div>
      </div>
      <el-button size="small" link @click="$emit('clear-feedback')" style="margin-top: 8px">关闭</el-button>
    </el-alert>
    
    <template #footer><el-button @click="$emit('update:visible', false)">取消</el-button><el-button type="primary" @click="$emit('save')">{{ isEdit?'保存修改':'确认销售' }}</el-button></template>
  </el-dialog>
</template>

<script setup>
import ordersApi from '../api/orders'
import ImageUpload from './ImageUpload.vue'
import OrderItemEditor from './OrderItemEditor.vue'
import { useEnumsStore } from '../stores/enums'

const enumsStore = useEnumsStore()

const props = defineProps({
  visible: Boolean,
  isEdit: Boolean,
  form: { type: Object, required: true },
  products: { type: Array, default: () => [] },
  customers: { type: Array, default: () => [] },
  orderTotal: { type: Number, default: 0 },
  onProductChange: { type: Function, required: true },
  operationFeedback: { type: Object, default: null }
})

const emit = defineEmits(['update:visible', 'save', 'clear-feedback'])
</script>