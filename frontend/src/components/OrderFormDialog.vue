<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    :title="isEdit ? `编辑${titleName}单` : `新建${titleName}单`"
    width="680px"
    destroy-on-close
  >
    <el-form label-width="80px">
      <!-- 客户/供应商 -->
      <el-form-item :label="partnerLabel">
        <el-select
          v-if="partnerMode === 'select'"
          v-model="form[partnerField]"
          filterable clearable
          :placeholder="'选择' + partnerLabel"
          style="width:100%"
        >
          <el-option v-for="p in partners" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select
          v-else
          v-model="form[partnerField]"
          filterable allow-create default-first-option clearable
          :placeholder="'选择或输入' + partnerLabel + '名(可空=散客)'"
          style="width:100%"
        >
          <el-option v-for="p in partners" :key="p.id" :label="p.name" :value="p.name" />
        </el-select>
      </el-form-item>

      <!-- 日期（仅销售新建时） -->
      <el-form-item v-if="showDate && !isEdit" label="销售日期">
        <el-date-picker v-model="form.sale_date" type="date" placeholder="选择日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width:100%" />
      </el-form-item>

      <!-- 税率 -->
      <el-form-item v-if="showTaxRate && (!isEdit || showTaxRateOnEdit)" label="税率">
        <el-select v-model="form.tax_rate" style="width:100%">
          <el-option label="0%" :value="0" />
          <el-option label="3%" :value="0.03" />
          <el-option label="6%" :value="0.06" />
          <el-option label="9%" :value="0.09" />
          <el-option label="13%" :value="0.13" />
        </el-select>
      </el-form-item>

      <!-- 是否开票 -->
      <el-form-item label="是否开票">
        <el-switch v-model="form.has_invoice" />
      </el-form-item>

      <!-- 支付方式（仅采购） -->
      <el-form-item v-if="showPaymentMethod" label="支付方式">
        <el-select v-model="form.payment_method" style="width:100%">
          <el-option v-for="opt in enumsStore.paymentMethodOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </el-form-item>

      <!-- 支付状态 -->
      <el-form-item label="支付状态">
        <el-select v-model="form.payment_status" style="width:100%">
          <template v-if="!isEdit || useEnumsForPayment">
            <el-option v-for="opt in enumsStore.paymentStatusOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </template>
          <template v-else>
            <el-option label="未支付" value="unpaid" />
            <el-option label="已支付" value="paid" />
          </template>
        </el-select>
      </el-form-item>

      <!-- 备注 -->
      <el-form-item label="备注">
        <el-input v-model="form.notes" type="textarea" :rows="2" />
      </el-form-item>

      <!-- 附件图片 -->
      <el-form-item label="附件图片">
        <ImageUpload v-model="form.image_url" :business-type="businessType" :record-id="form.id||0" :update-api="data => updateApi(form.id, data)" />
      </el-form-item>
    </el-form>

    <OrderItemEditor
      :items="form.items"
      :products="products"
      :show-stock="showStock"
      :show-custom-price="showCustomPrice"
      :order-total="orderTotal"
      v-model:total-price="form.total_price"
      :title="itemsTitle"
      @product-change="onProductChange"
    />

    <div v-if="isEdit && form.items.length===0" style="margin-top:8px;color:var(--el-color-danger);font-size:12px">
      <el-icon><Warning /></el-icon> 删除所有商品后保存将自动删除此{{ titleName }}单
    </div>

    <!-- 操作反馈 -->
    <el-alert
      v-if="operationFeedback?.show"
      :type="operationFeedback.type"
      :title="operationFeedback.message"
      :closable="false"
      style="margin-top:12px"
    >
      <div v-if="operationFeedback.details?.length" style="margin-top:8px;font-size:12px">
        <div v-for="(detail, idx) in operationFeedback.details" :key="idx">
          {{ detail.label }}: <b>{{ detail.value }}</b>
        </div>
      </div>
      <el-button size="small" link @click="$emit('clear-feedback')" style="margin-top:8px">关闭</el-button>
    </el-alert>

    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" @click="$emit('save')">{{ isEdit ? '保存修改' : confirmText }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import ImageUpload from './ImageUpload.vue'
import OrderItemEditor from './OrderItemEditor.vue'
import { useEnumsStore } from '../stores/enums'

const enumsStore = useEnumsStore()

defineProps({
  visible: Boolean,
  isEdit: Boolean,
  form: { type: Object, required: true },
  products: { type: Array, default: () => [] },
  partners: { type: Array, default: () => [] },
  orderTotal: { type: Number, default: 0 },
  onProductChange: { type: Function, required: true },
  operationFeedback: { type: Object, default: null },

  titleName: { type: String, default: '' },
  partnerLabel: { type: String, default: '' },
  partnerMode: { type: String, default: 'select' },
  partnerField: { type: String, default: 'supplier_id' },
  showDate: { type: Boolean, default: false },
  showTaxRate: { type: Boolean, default: true },
  showTaxRateOnEdit: { type: Boolean, default: true },
  showPaymentMethod: { type: Boolean, default: false },
  showStock: { type: Boolean, default: false },
  showCustomPrice: { type: Boolean, default: false },
  useEnumsForPayment: { type: Boolean, default: true },
  businessType: { type: String, default: 'purchase' },
  itemsTitle: { type: String, default: '' },
  confirmText: { type: String, default: '确认' },
  updateApi: { type: Function, default: () => {} }
})

defineEmits(['update:visible', 'save', 'clear-feedback'])
</script>

<style scoped></style>
