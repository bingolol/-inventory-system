<template>
  <div>
    <el-row :gutter="16" style="margin-bottom: 16px;">
      <el-col :span="8">
        <el-card shadow="never">
          <div style="text-align:center;">
            <div style="font-size:28px;font-weight:700;color:var(--success);">¥{{ summary.month_income?.toLocaleString() || '0.00' }}</div>
            <div style="color:var(--text-secondary);margin-top:4px;">本月收入</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never">
          <div style="text-align:center;">
            <div style="font-size:28px;font-weight:700;color:var(--danger);">¥{{ summary.month_expense?.toLocaleString() || '0.00' }}</div>
            <div style="color:var(--text-secondary);margin-top:4px;">本月支出</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never">
          <div style="text-align:center;">
            <div style="font-size:28px;font-weight:700;color:var(--primary);">¥{{ summary.month_balance?.toLocaleString() || '0.00' }}</div>
            <div style="color:var(--text-secondary);margin-top:4px;">本月结余</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 16px;">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span style="font-weight:600;">分类统计</span>
              <el-radio-group v-model="categoryChartType" size="small" @change="loadCategorySummary">
                <el-radio-button value="expense">支出</el-radio-button>
                <el-radio-button value="income">收入</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <v-chart :option="categoryChartOption" autoresize style="height: 300px;" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span style="font-weight:600;">月度趋势</span>
              <el-radio-group v-model="monthlyChartType" size="small" @change="loadMonthlySummary">
                <el-radio-button value="all">全部</el-radio-button>
                <el-radio-button value="expense">支出</el-radio-button>
                <el-radio-button value="income">收入</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <v-chart :option="monthlyChartOption" autoresize style="height: 300px;" />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-weight:600;">流水记录</span>
          <el-button type="primary" size="small" @click="showDialog()"><el-icon><Plus /></el-icon> 记一笔</el-button>
        </div>
      </template>
      <div style="margin-bottom:12px;display:flex;gap:12px;flex-wrap:wrap;">
        <el-select v-model="typeFilter" placeholder="类型筛选" clearable style="width:120px" @change="onTypeChange">
          <el-option label="收入" value="income" />
          <el-option label="支出" value="expense" />
        </el-select>
        <el-select v-model="categoryFilter" placeholder="分类筛选" clearable style="width:130px" @change="loadData">
          <el-option v-for="cat in filterCategoryOptions" :key="cat" :label="cat" :value="cat" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="loadData" />
        <el-button @click="loadData">查询</el-button>
      </div>
      <el-table :data="list" stripe style="width:100%">
        <el-table-column prop="date" label="日期" width="120">
          <template #default="{ row }">{{ row.date?.slice(0, 10) }}</template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="90">
          <template #default="{ row }">
            <el-tag :type="row.type === 'income' ? 'success' : 'danger'" size="small">
              {{ row.type === 'income' ? '收入' : '支出' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="120" />
        <el-table-column prop="amount" label="金额" width="120">
          <template #default="{ row }">
            <span :style="{ color: row.type === 'income' ? 'var(--success)' : 'var(--danger)', fontWeight: 600 }">
              {{ row.type === 'income' ? '+' : '-' }}¥{{ formatMoney(row.amount) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="备注" min-width="150" />
        <el-table-column prop="image_url" label="附件" width="70" align="center">
          <template #default="{ row }">
            <el-image v-if="row.image_url" :src="resolveImageUrl(row.image_url)" style="width:36px;height:36px;" fit="cover" :preview-src-list="[resolveImageUrl(row.image_url)]" />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="showDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除?" @confirm="handleDelete(row.id)">
              <template #reference><el-button size="small" link type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;padding:10px 16px;background:var(--fill-light);border-radius:6px;">
        <div style="display:flex;gap:24px;font-size:14px;">
          <span>筛选合计：</span>
          <span style="color:var(--success);font-weight:600;">收入 ¥{{ formatMoney(filterSummary.sum_income) }}</span>
          <span style="color:var(--danger);font-weight:600;">支出 ¥{{ formatMoney(filterSummary.sum_expense) }}</span>
          <span style="color:var(--primary);font-weight:600;">结余 ¥{{ formatMoney(filterSummary.sum_balance) }}</span>
        </div>
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next" @current-change="loadData" @size-change="loadData" />
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑记录' : '记一笔'" width="460px" destroy-on-close>
      <el-form :model="form" label-width="80px" style="padding-right:20px;">
        <el-form-item label="类型" required>
          <el-radio-group v-model="form.type">
            <el-radio-button value="income">收入</el-radio-button>
            <el-radio-button value="expense">支出</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="金额" required>
          <el-input-number v-model="form.amount" :min="0.01" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" placeholder="请选择分类" clearable>
            <el-option v-for="cat in categoryOptions" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期" required>
          <el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="附件图片">
          <ImageUpload v-model="form.image_url" business-type="personal" :record-id="editingId || 0" :update-api="personalApi.updatePersonalTransaction" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import personalApi from '../api/personal'
import commonApi from '../api/common'
import { formatMoney } from '../api/common'
import { resolveImageUrl } from '../api/index'
import ImageUpload from '../components/ImageUpload.vue'
import { useAccountAwareData } from '../composables/useAccountAwareData'

use([BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const summary = ref({})
const typeFilter = ref('')
const categoryFilter = ref('')
const filterSummary = ref({ sum_income: 0, sum_expense: 0, sum_balance: 0 })
const dateRange = ref(null)
const dialogVisible = ref(false)
const editingId = ref(null)

// 图表相关
const categoryChartType = ref('expense')
const categorySummaryData = ref([])
const monthlyChartType = ref('all')
const monthlySummaryData = ref([])

const categoryChartOption = computed(() => {
  const data = categorySummaryData.value
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 50, right: 20, top: 20, bottom: 20 },
    xAxis: { type: 'value', axisLabel: { formatter: val => val >= 10000 ? (val / 10000).toFixed(1) + '万' : val } },
    yAxis: { type: 'category', data: data.map(d => d.category), inverse: true },
    series: [{
      type: 'bar',
      data: data.map(d => d.total),
      itemStyle: { color: categoryChartType.value === 'income' ? '#67c23a' : '#f56c6c', borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right', formatter: params => '¥' + params.value.toLocaleString() }
    }]
  }
})

const monthlyChartOption = computed(() => {
  const data = monthlySummaryData.value
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: data.map(d => d.label) },
    yAxis: { type: 'value', axisLabel: { formatter: val => val >= 10000 ? (val / 10000).toFixed(1) + '万' : val } },
    series: [{
      type: 'bar',
      data: data.map(d => d.total),
      itemStyle: { color: monthlyChartType.value === 'income' ? '#67c23a' : monthlyChartType.value === 'expense' ? '#f56c6c' : '#409eff', borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: 'top', formatter: params => '¥' + params.value.toLocaleString() }
    }]
  }
})
const form = ref({ type: 'expense', amount: 0, category: '', date: '', description: '', image_url: '' })

// 分类选项（从API获取，根据收入/支出动态切换）
const expenseCategories = ref([])
const incomeCategories = ref([])
const categoryOptions = computed(() => form.value.type === 'income' ? incomeCategories.value : expenseCategories.value)

// 筛选栏分类选项：根据类型筛选动态切换，未选类型时显示全部
const filterCategoryOptions = computed(() => {
  if (typeFilter.value === 'income') return incomeCategories.value
  if (typeFilter.value === 'expense') return expenseCategories.value
  return [...incomeCategories.value, ...expenseCategories.value]
})

// 类型筛选变更时清空分类筛选并重新加载
const onTypeChange = () => {
  categoryFilter.value = ''
  loadData()
}

const loadEnums = async () => {
  try {
    const enums = await commonApi.getEnums()
    expenseCategories.value = enums.values.personal_expense_categories
    incomeCategories.value = enums.values.personal_income_categories
  } catch (e) { /* 降级：保留空列表 */ }
}

const loadData = async () => {
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (typeFilter.value) params.type = typeFilter.value
    if (categoryFilter.value) params.category = categoryFilter.value
    if (dateRange.value) { params.start_date = dateRange.value[0]; params.end_date = dateRange.value[1] }
    const res = await personalApi.getPersonalTransactions(params)
    total.value = res.total
    list.value = res.items
    filterSummary.value = { sum_income: res.sum_income || 0, sum_expense: res.sum_expense || 0, sum_balance: res.sum_balance || 0 }
  } catch (e) { ElMessage.error('加载失败') }
}

const loadSummary = async () => {
  try {
    summary.value = await personalApi.getPersonalSummary()
  } catch (e) { /* ignore */ }
}

const loadCategorySummary = async () => {
  try {
    const params = { type: categoryChartType.value }
    if (dateRange.value) { params.start_date = dateRange.value[0]; params.end_date = dateRange.value[1] }
    categorySummaryData.value = await personalApi.getPersonalCategorySummary(params)
  } catch (e) { console.error(e) }
}

const loadMonthlySummary = async () => {
  try {
    const params = {}
    if (monthlyChartType.value !== 'all') params.type = monthlyChartType.value
    monthlySummaryData.value = await personalApi.getPersonalMonthlySummary(params)
  } catch (e) { console.error(e) }
}

const showDialog = (row) => {
  if (row) {
    editingId.value = row.id
    form.value = {
      type: row.type,
      amount: Number(row.amount) || 0,
      category: row.category || '',
      date: row.date?.slice(0, 10) || '',
      description: row.description || '',
      image_url: row.image_url || ''
    }
  } else {
    editingId.value = null
    const today = new Date().toISOString().slice(0, 10)
    form.value = { type: 'expense', amount: 0, category: '', date: today, description: '' }
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.amount || form.value.amount <= 0) { ElMessage.warning('金额必须大于0'); return }
  if (!form.value.date) { ElMessage.warning('请选择日期'); return }
  try {
    if (editingId.value) {
      await personalApi.updatePersonalTransaction(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await personalApi.createPersonalTransaction(form.value)
      ElMessage.success('记录成功')
    }
    dialogVisible.value = false
    loadData()
    loadSummary()
    loadCategorySummary()
    loadMonthlySummary()
  } catch (e) { ElMessage.error('保存失败') }
}

const handleDelete = async (id) => {
  try {
    await personalApi.deletePersonalTransaction(id)
    ElMessage.success('已删除')
    loadData()
    loadSummary()
    loadCategorySummary()
    loadMonthlySummary()
  } catch (e) { ElMessage.error('删除失败') }
}

useAccountAwareData(loadData, loadSummary, loadCategorySummary, loadMonthlySummary)
loadEnums()
</script>