<template>
  <div class="invoices-container">
    <el-card shadow="never">
      <template #header>
        <PageHeader title="发票管理">
          <template #actions>
            <el-button type="primary" @click="openCreateDialog">
              <el-icon><Plus /></el-icon> 新增发票
            </el-button>
          </template>
        </PageHeader>
      </template>

      <FilterBar @search="search" @reset="resetFilters">
        <el-form :inline="true" :model="filters" class="inline-filter-form">
          <el-form-item label="方向" class="filter-item">
            <el-select v-model="filters.direction" placeholder="全部" clearable>
              <el-option v-for="opt in enumsStore.invoiceDirectionOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="类型" class="filter-item">
            <el-select v-model="filters.invoice_type" placeholder="全部" clearable>
              <el-option v-for="opt in enumsStore.invoiceTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="年份" class="filter-item">
            <el-select v-model="filters.year" placeholder="全部" clearable>
              <el-option v-for="year in years" :key="year" :label="year" :value="year" />
            </el-select>
          </el-form-item>
          <el-form-item label="季度" class="filter-item">
            <el-select v-model="filters.quarter" placeholder="全部" clearable>
              <el-option label="第一季度" value="1" />
              <el-option label="第二季度" value="2" />
              <el-option label="第三季度" value="3" />
              <el-option label="第四季度" value="4" />
            </el-select>
          </el-form-item>
          <el-form-item label="认证状态" class="filter-item">
            <el-select v-model="filters.certification_status" placeholder="全部" clearable>
              <el-option v-for="opt in enumsStore.certificationStatusOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
          </el-form-item>
        </el-form>
      </FilterBar>

      <InvoiceTaxStats
        :output-tax="taxStats.outputTax"
        :input-tax="taxStats.inputTax"
        :tax-payable="taxStats.taxPayable"
      />

      <InvoiceList
        :invoices="list"
        :loading="loading"
        @preview-pdf="previewPdf"
        @preview-image="previewImage"
        @edit="openEditDialog"
        @reverse="handleReverse"
        @certify="handleCertify"
        @uncertify="handleUncertify"
      />

      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="pagination.page.value"
          v-model:page-size="pagination.pageSize.value"
          :total="pagination.total.value"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @current-change="loadInvoices"
          @size-change="pagination.onSizeChange"
        />
      </div>
    </el-card>

    <InvoiceFormDialog
      v-model="dialogVisible"
      :invoice="editingInvoice"
      @submit="handleSubmit"
    />

    <el-dialog v-model="pdfVisible" title="PDF预览" width="800px" height="600px">
      <iframe :src="pdfUrl" width="100%" height="500px" frameborder="0"></iframe>
    </el-dialog>

    <el-dialog v-model="imagePreviewVisible" title="图片预览" width="600px">
      <el-image v-if="imagePreviewUrl" :src="imagePreviewUrl" style="width:100%;" fit="contain" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import invoicesApi from '../api/invoices'
import { resolveImageUrl, handleError, baseURL } from '../api/index'
import { currentYear, currentQuarter, generateYears } from '../utils/date'
import { useEnumsStore } from '../stores/enums'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { useList } from '../composables/useList'
import PageHeader from '../components/PageHeader.vue'
import FilterBar from '../components/FilterBar.vue'
import InvoiceTaxStats from '../components/invoices/InvoiceTaxStats.vue'
import InvoiceList from '../components/invoices/InvoiceList.vue'
import InvoiceFormDialog from '../components/invoices/InvoiceFormDialog.vue'

const enumsStore = useEnumsStore()

const defaultFilters = {
  direction: '',
  invoice_type: '',
  year: '',
  quarter: '',
  certification_status: ''
}

const { list, loading, filters, pagination, loadData } = useList({
  api: invoicesApi,
  method: 'getInvoices',
  defaultFilters,
  buildParams: (f) => {
    const params = {}
    for (const [key, value] of Object.entries(f)) {
      if (value !== '' && value !== null && value !== undefined) {
        params[key] = value
      }
    }
    return params
  },
  onError: (e) => handleError(e, { defaultMsg: '获取发票列表失败，请检查筛选条件是否正确', feedback: 'silent' })
})

const years = generateYears(-2, 2)

const taxStats = ref({
  outputTax: 0,
  inputTax: 0,
  taxPayable: 0
})

async function fetchTaxStats() {
  try {
    const year = filters.value.year || currentYear()
    const quarter = filters.value.quarter || currentQuarter()
    const res = await invoicesApi.getTaxReport(year, quarter)
    taxStats.value = {
      outputTax: Number(res.output_tax) || 0,
      inputTax: Number(res.input_tax) || 0,
      taxPayable: Number(res.tax_payable) || 0
    }
  } catch (e) {
    handleError(e, { defaultMsg: '获取税务统计失败，请检查本期是否有发票数据', feedback: 'silent' })
  }
}

async function loadInvoices() {
  await loadData()
  await fetchTaxStats()
}

function search() {
  pagination.resetPage()
  loadInvoices()
}

function resetFilters() {
  filters.value = { ...defaultFilters }
  pagination.resetPage()
  loadInvoices()
}

const dialogVisible = ref(false)
const editingInvoice = ref(null)

function openCreateDialog() {
  editingInvoice.value = null
  dialogVisible.value = true
}

function openEditDialog(row) {
  editingInvoice.value = row
  dialogVisible.value = true
}

async function handleSubmit({ id, payload }) {
  try {
    if (id) {
      await invoicesApi.updateInvoice(id, payload)
      ElMessage.success('发票已更新')
    } else {
      await invoicesApi.createInvoice(payload)
      ElMessage.success('发票已创建')
    }
    dialogVisible.value = false
    loadInvoices()
  } catch (error) {
    handleError(error, { defaultMsg: '保存发票失败，请检查输入数据是否正确' })
  }
}

async function handleReverse(row) {
  try {
    await invoicesApi.reverseInvoice(row.id, '前端红冲')
    ElMessage.success('发票已红冲')
    loadInvoices()
  } catch (error) {
    handleError(error, { defaultMsg: '红冲发票失败，请检查该发票是否允许红冲' })
  }
}

async function handleCertify(id) {
  try {
    await invoicesApi.certifyInvoice(id)
    ElMessage.success('认证成功')
    loadInvoices()
  } catch (error) {
    handleError(error, { defaultMsg: '认证发票失败，请检查发票认证状态' })
  }
}

async function handleUncertify(row) {
  try {
    await ElMessageBox.confirm('确认将发票认证状态恢复为"待认证"？', '提示', { type: 'warning' })
    await invoicesApi.updateInvoice(row.id, { certification_status: 'pending' })
    ElMessage.success('已取消认证')
    loadInvoices()
  } catch (error) {
    if (error !== 'cancel') {
      handleError(error, { defaultMsg: '取消认证失败' })
    }
  }
}

const pdfVisible = ref(false)
const pdfUrl = ref('')
const imagePreviewVisible = ref(false)
const imagePreviewUrl = ref('')

function previewPdf(id) {
  pdfUrl.value = `${baseURL}/invoices/${id}/pdf`
  pdfVisible.value = true
}

function previewImage(row) {
  imagePreviewUrl.value = resolveImageUrl(row.image_url)
  imagePreviewVisible.value = true
}

useAccountAwareData(loadInvoices)
onMounted(() => {
  enumsStore.fetchEnums()
})
</script>

<style scoped>
.filter-item {
  margin-bottom: 0;
}
.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
