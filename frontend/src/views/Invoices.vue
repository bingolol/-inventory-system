<template>
  <div class="invoices-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">发票管理</span>
          <el-button type="primary" @click="dialogVisible = true"><el-icon><Plus /></el-icon> 新增发票</el-button>
        </div>
      </template>
    
    <!-- 筛选条件 -->
    <el-form :inline="true" :model="filterForm" class="filter-bar">
      <el-form-item label="方向">
        <el-select v-model="filterForm.direction" placeholder="全部">
          <el-option v-for="opt in enumsStore.invoiceDirectionOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="类型">
        <el-select v-model="filterForm.invoice_type" placeholder="全部">
          <el-option v-for="opt in enumsStore.invoiceTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="年份">
        <el-select v-model="filterForm.year" placeholder="全部">
          <el-option v-for="year in years" :key="year" :label="year" :value="year" />
        </el-select>
      </el-form-item>
      <el-form-item label="季度">
        <el-select v-model="filterForm.quarter" placeholder="全部">
          <el-option label="第一季度" value="1" />
          <el-option label="第二季度" value="2" />
          <el-option label="第三季度" value="3" />
          <el-option label="第四季度" value="4" />
        </el-select>
      </el-form-item>
      <el-form-item label="认证状态">
        <el-select v-model="filterForm.certification_status" placeholder="全部">
          <el-option v-for="opt in enumsStore.certificationStatusOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="getInvoices">查询</el-button>
        <el-button @click="resetFilter">重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 本季度税务统计 -->
    <div class="inv-stats">
      <div class="inv-stat-item">
        <span class="inv-stat-label">销项税额</span>
        <span class="inv-stat-value c-primary">{{ formatMoney(taxStats.outputTax) }}</span>
      </div>
      <div class="inv-stat-item">
        <span class="inv-stat-label">进项税额</span>
        <span class="inv-stat-value c-success">{{ formatMoney(taxStats.inputTax) }}</span>
      </div>
      <div class="inv-stat-item">
        <span class="inv-stat-label">应纳税额</span>
        <span class="inv-stat-value c-danger">{{ formatMoney(taxStats.taxPayable) }}</span>
      </div>
    </div>

    <!-- 发票列表 -->
    <el-table :data="invoices" stripe v-loading="loading" style="width: 100%">
      <template #empty>
        <el-empty description="暂无发票记录" />
      </template>
      <el-table-column prop="invoice_no" label="发票号码" min-width="150" />
      <el-table-column prop="direction" label="方向" min-width="80" align="center">
        <template #default="scope">
          <span class="status-badge" :class="scope.row.direction === 'out' ? 'primary' : 'success'">
            {{ enumsStore.getLabel('invoice_direction', scope.row.direction) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="invoice_type" label="类型" min-width="80" align="center">
        <template #default="scope">
          <span class="status-badge" :class="scope.row.invoice_type === 'special' ? 'warning' : 'info'">
            {{ enumsStore.getLabel('invoice_type', scope.row.invoice_type) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="tax_rate" label="税率" min-width="80" align="center">
        <template #default="scope">
          {{ Number(scope.row.tax_rate * 100).toFixed(0) }}%
        </template>
      </el-table-column>
      <el-table-column prop="amount_without_tax" label="不含税金额" min-width="120" align="right">
        <template #default="scope">
          {{ formatMoney(scope.row.amount_without_tax) }}
        </template>
      </el-table-column>
      <el-table-column prop="tax_amount" label="税额" min-width="100" align="right">
        <template #default="scope">
          {{ formatMoney(scope.row.tax_amount) }}
        </template>
      </el-table-column>
      <el-table-column prop="amount_with_tax" label="价税合计" min-width="120" align="right">
        <template #default="scope">
          {{ formatMoney(scope.row.amount_with_tax) }}
        </template>
      </el-table-column>
      <el-table-column prop="counterparty_name" label="对方名称" min-width="150" />
      <el-table-column label="开票日期" min-width="120">
        <template #default="{ row }">{{ formatDate(row.issue_date) }}</template>
      </el-table-column>
      <el-table-column prop="certification_status" label="认证状态" min-width="100" align="center">
        <template #default="scope">
          <span class="status-badge" :class="getCertificationType(scope.row.certification_status)">
            {{ getCertificationText(scope.row.certification_status) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240" align="center">
        <template #default="scope">
          <el-button v-if="scope.row.pdf_path" @click="previewPdf(scope.row.id)" type="info" size="small">
            预览
          </el-button>
          <el-button v-if="scope.row.image_url" @click="previewImage(scope.row)" type="info" size="small">
            图片
          </el-button>
          <el-button @click="editInvoice(scope.row)" size="small" link type="primary">
            编辑
          </el-button>
          <el-popconfirm v-if="!scope.row.is_reversed" title="确定红冲此发票？（关联订单将自动取消）" @confirm="reverseInvoice(scope.row.id)">
            <template #reference>
              <el-button type="warning" size="small">红冲</el-button>
            </template>
          </el-popconfirm>
          <el-button v-if="scope.row.direction === 'in' && scope.row.invoice_type === 'special' && scope.row.certification_status !== 'certified'" @click="certifyInvoice(scope.row.id)" type="success" size="small">
            认证
          </el-button>
          <el-button v-else-if="scope.row.direction === 'in' && scope.row.invoice_type === 'special' && scope.row.certification_status === 'certified'" @click="uncertifyInvoice(scope.row)" type="warning" size="small">
            取消认证
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 筛选合计 -->
    <div class="inv-total">
      <span>筛选合计：</span>
      <span class="inv-total-item">不含税 ¥{{ formatMoney(totalAmountWithoutTax) }}</span>
      <span class="inv-total-item">税额 ¥{{ formatMoney(totalTaxAmount) }}</span>
      <span class="inv-total-highlight">价税合计 ¥{{ formatMoney(totalAmountWithTax) }}</span>
    </div>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'create' ? '新增发票' : '编辑发票'"
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
            <el-option label="1%" :value="0.01" />
            <el-option label="3%" :value="0.03" />
            <el-option label="6%" :value="0.06" />
            <el-option label="9%" :value="0.09" />
            <el-option label="13%" :value="0.13" />
          </el-select>
        </el-form-item>
        <el-form-item label="PDF上传">
          <el-upload
            class="upload-demo"
            :action="`${baseURL}/invoices/upload`"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :before-upload="beforeUpload"
            :headers="{ 'X-Account-ID': String(accountId) }"
          >
            <el-button type="primary">点击上传</el-button>
            <template #tip>
              <div class="el-upload__tip">
                只能上传 PDF 文件
              </div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="附件图片">
          <ImageUpload v-model="invoiceForm.image_url" business-type="invoice" :record-id="currentInvoiceId || 0" :update-api="invoicesApi.updateInvoice" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="invoiceForm.notes" type="textarea" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveInvoice">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- PDF预览弹窗 -->
    <el-dialog
      v-model="pdfVisible"
      title="PDF预览"
      width="800px"
      height="600px"
    >
      <iframe :src="pdfUrl" width="100%" height="500px" frameborder="0"></iframe>
    </el-dialog>
    <!-- 图片预览弹窗 -->
    <el-dialog v-model="imagePreviewVisible" title="图片预览" width="600px">
      <el-image v-if="imagePreviewUrl" :src="imagePreviewUrl" style="width:100%;" fit="contain" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useAccountStore } from '../stores/account'
const accountStore = useAccountStore()
import invoicesApi from '../api/invoices'
import { resolveImageUrl, handleError, baseURL } from '../api/index'
import { formatMoney, formatDate } from '../utils/format'
import { calculateInvoiceAmounts } from '../utils/invoiceCalc'
import ImageUpload from '../components/ImageUpload.vue'
import { useEnumsStore } from '../stores/enums'
import { useAccountAwareData } from '../composables/useAccountAwareData'
const accountId = computed(() => accountStore.currentAccount?.id ?? '')
const enumsStore = useEnumsStore()

// 发票列表
const invoices = ref([])
const loading = ref(false)

// 计算当前列表的金额总和
const totalAmountWithoutTax = computed(() => {
  return invoices.value.reduce((sum, item) => sum + (Number(item.amount_without_tax) || 0), 0)
})

const totalTaxAmount = computed(() => {
  return invoices.value.reduce((sum, item) => sum + (Number(item.tax_amount) || 0), 0)
})

const totalAmountWithTax = computed(() => {
  return invoices.value.reduce((sum, item) => sum + (Number(item.amount_with_tax) || 0), 0)
})

// 筛选表单
const filterForm = ref({
  direction: '',
  invoice_type: '',
  year: '',
  quarter: '',
  certification_status: ''
})
// 年份列表
const years = ref([])
// 本季度税务统计
const taxStats = ref({
  outputTax: 0,
  inputTax: 0,
  taxPayable: 0
})
// 弹窗相关
const dialogVisible = ref(false)
const dialogType = ref('create')
const currentInvoiceId = ref(null)
const amountInputType = ref('价税合计')
const invoiceForm = ref({
  invoice_no: '',
  direction: 'out',
  invoice_type: 'ordinary',
  tax_rate: 0.01,
  amount_without_tax: 0,
  tax_amount: 0,
  amount_with_tax: 0,
  counterparty_name: '',
  issue_date: '',
  pdf_path: '',
  image_url: '',
  notes: ''
})

// PDF预览
const pdfVisible = ref(false)
const pdfUrl = ref('')

// 图片预览
const imagePreviewVisible = ref(false)
const imagePreviewUrl = ref('')

// 生成年份列表
const generateYears = () => {
  const currentYear = new Date().getFullYear()
  for (let i = currentYear - 2; i <= currentYear + 2; i++) {
    years.value.push(i)
  }
}

// 获取当前季度
const getCurrentQuarter = () => Math.ceil((new Date().getMonth() + 1) / 3)

// 获取本季度税务统计
const fetchTaxStats = async (year, quarter) => {
  try {
    const y = year || new Date().getFullYear()
    const q = quarter || getCurrentQuarter()
    const taxRes = await invoicesApi.getTaxReport(y, q)
    taxStats.value = {
      outputTax: taxRes.output_tax || 0,
      inputTax: taxRes.input_tax || 0,
      taxPayable: taxRes.tax_payable || 0
    }
  } catch (e) { handleError(e, { defaultMsg: '获取税务统计失败，请检查本期是否有发票数据', feedback: 'silent' }) }
}

// 获取发票列表
const getInvoices = async () => {
  loading.value = true
  try {
    // 过滤空字符串参数，避免 422 错误
    const params = {}
    for (const [key, value] of Object.entries(filterForm.value)) {
      if (value !== '' && value !== null && value !== undefined) {
        params[key] = value
      }
    }
    const response = await invoicesApi.getInvoices(params)
    invoices.value = response?.items || []

    // 更新税务统计：优先用筛选器的年份/季度，否则用当前季度
    if (filterForm.value.year && filterForm.value.quarter) {
      await fetchTaxStats(parseInt(filterForm.value.year), parseInt(filterForm.value.quarter))
    } else {
      await fetchTaxStats()
    }
  } catch (error) {
    handleError(error, { defaultMsg: '获取发票列表失败，请检查筛选条件是否正确', feedback: 'silent' })
    invoices.value = []
  } finally {
    loading.value = false
  }
}

// 重置筛选
const resetFilter = () => {
  filterForm.value = {
    direction: '',
    invoice_type: '',
    year: '',
    quarter: '',
    certification_status: ''
  }
  getInvoices()
}

// 保存发票
const saveInvoice = async () => {
  try {
    const result = calculateInvoiceAmounts(
      invoiceForm.value.amount_with_tax,
      invoiceForm.value.amount_without_tax,
      invoiceForm.value.tax_rate,
      amountInputType.value,
    )
    invoiceForm.value.amount_without_tax = result.amount_without_tax
    invoiceForm.value.tax_amount = result.tax_amount
    invoiceForm.value.amount_with_tax = result.amount_with_tax

    if (dialogType.value === 'create') {
      await invoicesApi.createInvoice(invoiceForm.value)
    } else {
      await invoicesApi.updateInvoice(currentInvoiceId.value, invoiceForm.value)
    }
    dialogVisible.value = false
    getInvoices()
  } catch (error) {
    handleError(error, { defaultMsg: '保存发票失败，请检查输入数据是否正确' })
  }
}

// 编辑发票
const editInvoice = (invoice) => {
  dialogType.value = 'edit'
  currentInvoiceId.value = invoice.id
  invoiceForm.value = {
    invoice_no: invoice.invoice_no,
    direction: invoice.direction,
    invoice_type: invoice.invoice_type,
    tax_rate: invoice.tax_rate,
    amount_without_tax: Number(invoice.amount_without_tax) || 0,
    tax_amount: Number(invoice.tax_amount) || 0,
    amount_with_tax: Number(invoice.amount_with_tax) || 0,
    counterparty_name: invoice.counterparty_name,
    issue_date: invoice.issue_date ? new Date(invoice.issue_date) : '',
    pdf_path: invoice.pdf_path || '',
    image_url: invoice.image_url || '',
    notes: invoice.notes || '',
    certification_status: invoice.certification_status
  }
  amountInputType.value = '价税合计'
  dialogVisible.value = true
}

// 删除发票
const deleteInvoice = async (id) => {
  try {
    await invoicesApi.deleteInvoice(id)
    getInvoices()
  } catch (error) {
    handleError(error, { defaultMsg: '删除发票失败，请检查该发票是否已被红冲' })
  }
}

// 红冲发票
const reverseInvoice = async (id) => {
  try {
    await invoicesApi.reverseInvoice(id, '前端红冲')
    ElMessage.success('发票已红冲')
    getInvoices()
  } catch (error) {
    handleError(error, { defaultMsg: '红冲发票失败，请检查该发票是否允许红冲' })
  }
}

// 认证发票
const certifyInvoice = async (id) => {
  try {
    await invoicesApi.certifyInvoice(id)
    ElMessage.success('认证成功')
    getInvoices()
  } catch (error) {
    handleError(error, { defaultMsg: '认证发票失败，请检查发票认证状态' })
  }
}

// 取消认证
const uncertifyInvoice = async (row) => {
  try {
    await ElMessageBox.confirm('确认将发票认证状态恢复为"待认证"？', '提示', { type: 'warning' })
    await invoicesApi.updateInvoice(row.id, { certification_status: 'pending' })
    ElMessage.success('已取消认证')
    getInvoices()
  } catch (error) {
    if (error !== 'cancel') {
      handleError(error, { defaultMsg: '取消认证失败' })
    }
  }
}

// 预览PDF
const previewPdf = (id) => {
  pdfUrl.value = `${baseURL}/invoices/${id}/pdf`
  pdfVisible.value = true
}

// 预览图片
const previewImage = (invoice) => {
  imagePreviewUrl.value = resolveImageUrl(invoice.image_url)
  imagePreviewVisible.value = true
}

// 上传PDF
const handleUploadSuccess = (response) => {
  invoiceForm.value.pdf_path = response.pdf_path
}

const handleUploadError = () => {
  ElMessage.error('上传失败，请重试')
}

const beforeUpload = (file) => {
  const isPDF = file.type === 'application/pdf'
  if (!isPDF) {
    ElMessage.warning('只能上传 PDF 文件!')
  }
  return isPDF
}

// 获取认证状态类型
const getCertificationType = (status) => {
  switch (status) {
    case 'pending':
      return 'warning'
    case 'certified':
      return 'success'
    case 'n_a':
      return 'info'
    default:
      return 'default'
  }
}

// 获取认证状态文本
const getCertificationText = (status) => {
  switch (status) {
    case 'pending':
      return '未认证'
    case 'certified':
      return '已认证'
    case 'n_a':
      return '无需认证'
    default:
      return status
  }
}

// 监听金额变化
watch([() => invoiceForm.value.amount_with_tax, () => invoiceForm.value.amount_without_tax, () => invoiceForm.value.tax_rate], () => {
  if (amountInputType.value === '价税合计' && invoiceForm.value.amount_with_tax > 0 && invoiceForm.value.tax_rate > 0) {
    const amountWithTax = invoiceForm.value.amount_with_tax
    const taxRate = invoiceForm.value.tax_rate
    const amountWithoutTax = amountWithTax / (1 + taxRate)
    const taxAmount = amountWithTax - amountWithoutTax
    invoiceForm.value.amount_without_tax = parseFloat(amountWithoutTax.toFixed(2))
    invoiceForm.value.tax_amount = parseFloat(taxAmount.toFixed(2))
  } else if (amountInputType.value === '不含税金额' && invoiceForm.value.amount_without_tax > 0 && invoiceForm.value.tax_rate > 0) {
    const amountWithoutTax = invoiceForm.value.amount_without_tax
    const taxRate = invoiceForm.value.tax_rate
    const taxAmount = amountWithoutTax * taxRate
    const amountWithTax = amountWithoutTax + taxAmount
    invoiceForm.value.tax_amount = parseFloat(taxAmount.toFixed(2))
    invoiceForm.value.amount_with_tax = parseFloat(amountWithTax.toFixed(2))
  }
})

generateYears()
useAccountAwareData(getInvoices)
enumsStore.fetchEnums()
</script>

<style scoped>
.inv-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}
.inv-stat-item {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-left: 4px solid var(--primary);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.inv-stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
  letter-spacing: 0.5px;
}
.inv-stat-value {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.5px;
}
.inv-total {
  margin-top: 12px;
  padding: 10px 16px;
  background: var(--bg-elevated);
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 24px;
  font-size: 14px;
  color: var(--text-secondary);
}
.inv-total-item {
  font-weight: 600;
  color: var(--text-regular);
}
.inv-total-highlight {
  font-weight: 700;
  color: var(--primary);
}
</style>
