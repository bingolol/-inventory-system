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
    <el-form :inline="true" :model="filterForm" class="filter-form">
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
    <div class="tax-stats">
      <el-card class="stat-card">
        <template #header>
          <div class="card-header">
            <span>本季度税务统计</span>
          </div>
        </template>
        <div class="stats-content">
          <div class="stat-item">
            <span class="stat-label">销项税额</span>
            <span class="stat-value">{{ formatMoney(taxStats.outputTax) }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">进项税额</span>
            <span class="stat-value">{{ formatMoney(taxStats.inputTax) }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">应纳税额</span>
            <span class="stat-value text-red">{{ formatMoney(taxStats.taxPayable) }}</span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 发票列表 -->
    <el-table :data="invoices" stripe v-loading="loading" style="width: 100%">
      <template #empty>
        <el-empty description="暂无发票记录" />
      </template>
      <el-table-column prop="invoice_no" label="发票号码" width="150" />
      <el-table-column prop="direction" label="方向" width="80" align="center">
        <template #default="scope">
          <el-tag :type="scope.row.direction === 'out' ? 'primary' : 'success'">
            {{ enumsStore.getLabel('invoice_direction', scope.row.direction) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="invoice_type" label="类型" width="80" align="center">
        <template #default="scope">
          <el-tag :type="scope.row.invoice_type === 'special' ? 'warning' : 'info'">
            {{ enumsStore.getLabel('invoice_type', scope.row.invoice_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="tax_rate" label="税率" width="80" align="center">
        <template #default="scope">
          {{ Number(scope.row.tax_rate * 100).toFixed(0) }}%
        </template>
      </el-table-column>
      <el-table-column prop="amount_without_tax" label="不含税金额" width="120" align="right">
        <template #default="scope">
          {{ formatMoney(scope.row.amount_without_tax) }}
        </template>
      </el-table-column>
      <el-table-column prop="tax_amount" label="税额" width="100" align="right">
        <template #default="scope">
          {{ formatMoney(scope.row.tax_amount) }}
        </template>
      </el-table-column>
      <el-table-column prop="amount_with_tax" label="价税合计" width="120" align="right">
        <template #default="scope">
          {{ formatMoney(scope.row.amount_with_tax) }}
        </template>
      </el-table-column>
      <el-table-column prop="counterparty_name" label="对方名称" width="150" />
      <el-table-column prop="issue_date" label="开票日期" width="120" />
      <el-table-column prop="certification_status" label="认证状态" width="100" align="center">
        <template #default="scope">
          <el-tag :type="getCertificationType(scope.row.certification_status)">
            {{ getCertificationText(scope.row.certification_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" align="center">
        <template #default="scope">
          <el-button v-if="scope.row.pdf_path" @click="previewPdf(scope.row.id)" type="info" size="small">
            预览
          </el-button>
          <el-button v-if="scope.row.image_url" @click="previewImage(scope.row)" type="info" size="small">
            图片
          </el-button>
          <el-button @click="editInvoice(scope.row)" type="primary" size="small">
            编辑
          </el-button>
          <el-popconfirm title="确定删除此发票？" @confirm="deleteInvoice(scope.row.id)">
            <template #reference>
              <el-button type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
          <el-button v-if="scope.row.direction === 'in' && scope.row.invoice_type === 'special' && scope.row.certification_status === 'n_a'" @click="certifyInvoice(scope.row.id)" type="success" size="small">
            认证
          </el-button>
        </template>
      </el-table-column>
    </el-table>
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
            <el-option label="1%" value="0.01" />
            <el-option label="3%" value="0.03" />
            <el-option label="6%" value="0.06" />
            <el-option label="9%" value="0.09" />
            <el-option label="13%" value="0.13" />
          </el-select>
        </el-form-item>
        <el-form-item label="PDF上传">
          <el-upload
            class="upload-demo"
            action="/api/invoices/upload"
            :on-success="handleUploadSuccess"
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
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useAccountStore } from '../stores/account'
const accountStore = useAccountStore()
import invoicesApi from '../api/invoices'
import commonApi from '../api/common'
import { resolveImageUrl } from '../api/index'
import { formatMoney } from '../api/common'
import ImageUpload from '../components/ImageUpload.vue'
import { useEnumsStore } from '../stores/enums'
import { useAccountAwareData } from '../composables/useAccountAwareData'
const accountId = computed(() => accountStore.currentAccount.id)
const enumsStore = useEnumsStore()

// 发票列表
const invoices = ref([])
const loading = ref(false)
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
  } catch (e) { console.error('获取税务统计失败:', e) }
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
    console.error('获取发票列表失败:', error)
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
    // 计算税额
    if (amountInputType.value === '价税合计') {
      const amountWithTax = invoiceForm.value.amount_with_tax
      const taxRate = invoiceForm.value.tax_rate
      const amountWithoutTax = amountWithTax / (1 + taxRate)
      const taxAmount = amountWithTax - amountWithoutTax
      invoiceForm.value.amount_without_tax = parseFloat(amountWithoutTax.toFixed(2))
      invoiceForm.value.tax_amount = parseFloat(taxAmount.toFixed(2))
    } else {
      const amountWithoutTax = invoiceForm.value.amount_without_tax
      const taxRate = invoiceForm.value.tax_rate
      const taxAmount = amountWithoutTax * taxRate
      const amountWithTax = amountWithoutTax + taxAmount
      invoiceForm.value.tax_amount = parseFloat(taxAmount.toFixed(2))
      invoiceForm.value.amount_with_tax = parseFloat(amountWithTax.toFixed(2))
    }

    if (dialogType.value === 'create') {
      await invoicesApi.createInvoice(invoiceForm.value)
    } else {
      await invoicesApi.updateInvoice(currentInvoiceId.value, invoiceForm.value)
    }
    dialogVisible.value = false
    getInvoices()
  } catch (error) {
    console.error('保存发票失败:', error)
    ElMessage.error(error.response?.data?.detail || '保存发票失败')
  }
}

// 编辑发票
const editInvoice = (invoice) => {
  dialogType.value = 'edit'
  currentInvoiceId.value = invoice.id
  invoiceForm.value = {
    ...invoice,
    issue_date: invoice.issue_date ? new Date(invoice.issue_date) : ''
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
    console.error('删除发票失败:', error)
    ElMessage.error(error.response?.data?.detail || '删除发票失败')
  }
}

// 认证发票
const certifyInvoice = async (id) => {
  try {
    await invoicesApi.certifyInvoice(id)
    getInvoices()
  } catch (error) {
    console.error('认证发票失败:', error)
    ElMessage.error(error.response?.data?.detail || '认证发票失败')
  }
}

// 预览PDF
const previewPdf = (id) => {
  pdfUrl.value = `/api/invoices/${id}/pdf`
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
.invoices-container {
  padding: 20px;
}

.filter-form {
  margin-bottom: 20px;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.tax-stats {
  margin-bottom: 20px;
}

.stat-card {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats-content {
  display: flex;
  gap: 40px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 5px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
}

.text-red {
  color: #f56c6c;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
