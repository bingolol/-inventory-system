<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    @close="close"
    :close-on-click-modal="true"
    :title="isEdit ? '编辑发票' : '新增发票'"
    width="600px"
  >
    <el-form :model="invoiceForm" label-width="100px">
      <el-form-item label="发票号码" required>
        <el-input v-model="invoiceForm.invoice_no" placeholder="请输入发票号码" />
      </el-form-item>
      <el-form-item label="方向" required>
        <el-select v-model="invoiceForm.direction" placeholder="请选择方向">
          <el-option v-for="opt in enumsStore.invoiceDirectionOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="类型" required>
        <el-select v-model="invoiceForm.invoice_type" placeholder="请选择类型">
          <el-option v-for="opt in enumsStore.invoiceTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="对方名称" required>
        <el-input v-model="invoiceForm.counterparty_name" placeholder="请输入对方名称" />
      </el-form-item>
      <el-form-item label="开票日期" required>
        <el-date-picker v-model="invoiceForm.issue_date" type="date" placeholder="请选择日期" style="width: 100%" />
      </el-form-item>
      <el-form-item label="金额录入方式" required>
        <el-radio-group v-model="amountInputType">
          <el-radio value="价税合计" label="价税合计">价税合计</el-radio>
          <el-radio value="不含税金额" label="不含税金额">不含税金额</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="amountInputType === '价税合计'" label="价税合计" required>
        <el-input v-model.number="invoiceForm.amount_with_tax" placeholder="请输入价税合计" />
      </el-form-item>
      <el-form-item v-else label="不含税金额" required>
        <el-input v-model.number="invoiceForm.amount_without_tax" placeholder="请输入不含税金额" />
      </el-form-item>
      <el-form-item label="税率" required>
        <el-select v-model.number="invoiceForm.tax_rate" placeholder="请选择税率">
          <el-option v-for="opt in TAX_RATE_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="PDF上传">
        <el-upload
          class="upload-demo"
          :action="uploadUrl"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :before-upload="beforeUpload"
          :headers="uploadHeaders"
        >
          <el-button type="primary">点击上传</el-button>
          <template #tip>
            <div class="el-upload__tip">只能上传 PDF 文件</div>
          </template>
        </el-upload>
      </el-form-item>
      <el-form-item label="附件图片">
        <ImageUpload v-model="invoiceForm.image_url" business-type="invoice" :record-id="recordId" :update-api="invoicesApi.updateInvoice" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="invoiceForm.notes" type="textarea" placeholder="请输入备注" />
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="close">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import invoicesApi from '../../api/invoices'
import { baseURL } from '../../api/index'
import { calculateInvoiceAmounts } from '../../utils/invoiceCalc'
import ImageUpload from '../ImageUpload.vue'
import { useEnumsStore } from '../../stores/enums'
import { useAccountStore } from '../../stores/account'
import { TAX_RATE_OPTIONS } from '../../constants/taxRates'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  invoice: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue', 'submit'])

const enumsStore = useEnumsStore()
const accountStore = useAccountStore()

const isEdit = computed(() => !!props.invoice)
const recordId = computed(() => props.invoice?.id || 0)
const accountId = computed(() => accountStore.currentAccount?.id ?? '')

const uploadUrl = computed(() => `${baseURL}/invoices/upload`)
const uploadHeaders = computed(() => ({ 'X-Account-ID': String(accountId.value) }))

const amountInputType = ref('价税合计')

const defaultForm = () => ({
  invoice_no: '',
  direction: 'out',
  invoice_type: 'ordinary',
  tax_rate: 0.01,
  amount_without_tax: 0,
  tax_amount: 0,
  amount_with_tax: 0,
  counterparty_name: '',
  issue_date: '',
  certification_status: '',
  pdf_path: '',
  image_url: '',
  notes: ''
})

const invoiceForm = ref(defaultForm())

watch(() => props.modelValue, (visible) => {
  if (visible) {
    resetForm()
  }
})

watch(() => props.invoice, () => {
  if (props.modelValue) {
    resetForm()
  }
})

onMounted(() => {
  if (props.modelValue) {
    resetForm()
  }
})

function resetForm() {
  if (props.invoice) {
    invoiceForm.value = {
      invoice_no: props.invoice.invoice_no,
      direction: props.invoice.direction,
      invoice_type: props.invoice.invoice_type,
      tax_rate: Number(props.invoice.tax_rate) || 0,
      amount_without_tax: Number(props.invoice.amount_without_tax) || 0,
      tax_amount: Number(props.invoice.tax_amount) || 0,
      amount_with_tax: Number(props.invoice.amount_with_tax) || 0,
      counterparty_name: props.invoice.counterparty_name,
      issue_date: props.invoice.issue_date ? new Date(props.invoice.issue_date) : '',
      pdf_path: props.invoice.pdf_path || '',
      image_url: props.invoice.image_url || '',
      notes: props.invoice.notes || '',
      certification_status: props.invoice.certification_status
    }
    amountInputType.value = '价税合计'
  } else {
    invoiceForm.value = defaultForm()
    amountInputType.value = '价税合计'
  }
}

function close() {
  emit('update:modelValue', false)
}

async function save() {
  const payload = buildPayload()
  emit('submit', { id: props.invoice?.id, payload })
}

function buildPayload() {
  const form = { ...invoiceForm.value }
  if (!isEdit.value) {
    const result = calculateInvoiceAmounts(
      form.amount_with_tax,
      form.amount_without_tax,
      form.tax_rate,
      amountInputType.value
    )
    form.amount_without_tax = result.amount_without_tax
    form.tax_amount = result.tax_amount
    form.amount_with_tax = result.amount_with_tax
  }
  return form
}

function handleUploadSuccess(response) {
  invoiceForm.value.pdf_path = response.pdf_path
}

function handleUploadError() {
  ElMessage.error('上传失败，请重试')
}

function beforeUpload(file) {
  const isPDF = file.type === 'application/pdf'
  if (!isPDF) {
    ElMessage.warning('只能上传 PDF 文件!')
  }
  return isPDF
}
</script>
