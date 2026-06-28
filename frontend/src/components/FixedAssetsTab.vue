<template>
  <div class="fixed-assets-tab">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">固定资产管理</span>
          <el-button type="primary" @click="showCreate()"><el-icon><Plus /></el-icon> 新增资产</el-button>
        </div>
      </template>
      <div class="filter-bar">
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width:120px" @change="loadData">
          <el-option label="在用" value="在用" />
          <el-option label="停用" value="停用" />
          <el-option label="报废" value="报废" />
        </el-select>
      </div>
      <el-table :data="list" stripe style="width:100%" v-loading="loading">
        <template #empty>
          <el-empty description="暂无固定资产" />
        </template>
        <el-table-column prop="asset_code" label="资产编码" min-width="130" />
        <el-table-column prop="name" label="资产名称" min-width="120" />
        <el-table-column prop="category" label="类别" min-width="100" align="center">
          <template #default="{ row }">            <span class="status-badge" v-if="row.category">{{ row.category }}</span><span v-else>-</span></template>
        </el-table-column>
        <el-table-column prop="original_value" label="原值" min-width="120" align="right"><template #default="{ row }"><span class="money">¥{{ formatMoney(row.original_value) }}</span></template></el-table-column>
        <el-table-column prop="salvage_rate" label="残值率" min-width="80" align="center"><template #default="{ row }">{{ (Number(row.salvage_rate) * 100).toFixed(0) }}%</template></el-table-column>
        <el-table-column prop="useful_life" label="使用寿命(月)" min-width="110" align="center" />
        <el-table-column prop="depreciation_method" label="折旧方法" min-width="110" align="center" />
        <el-table-column prop="start_date" label="开始日期" min-width="110" />
        <el-table-column prop="accumulated_depreciation" label="累计折旧" min-width="120" align="right"><template #default="{ row }"><span class="money">¥{{ formatMoney(row.accumulated_depreciation) }}</span></template></el-table-column>
        <el-table-column label="净值" min-width="120" align="right"><template #default="{ row }"><span class="money">¥{{ formatMoney(Number(row.original_value) - Number(row.accumulated_depreciation)) }}</span></template></el-table-column>
        <el-table-column prop="status" label="状态" min-width="80" align="center"><template #default="{ row }"><span class="status-badge" :class="statusType(row.status)">{{ row.status }}</span></template></el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status !== '报废'" size="small" link type="primary" @click="showEdit(row)">编辑</el-button>
            <el-popconfirm v-if="row.status !== '报废'" title="确定处置此资产？（将标记为报废）" @confirm="handleDispose(row)"><template #reference><el-button size="small" link type="warning" style="margin-left:4px">处置</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑固定资产' : '新增固定资产'" width="680px" destroy-on-close>
      <el-form :model="form" label-width="0">
        <div class="fa-group" style="border-left-color:#4f6ef7;">
          <div class="fa-group-header">
            <span class="fa-group-tag" style="background:#eef1ff;color:#4f6ef7;">基本信息</span>
          </div>
          <div class="fa-group-body">
            <div class="fa-field"><span class="fa-label" style="min-width:80px;">资产编码</span><el-input v-model="form.asset_code" placeholder="如 FA-001" /></div>
            <div class="fa-field"><span class="fa-label" style="min-width:80px;">资产名称</span><el-input v-model="form.name" placeholder="如 办公电脑" /></div>
            <div class="fa-field"><span class="fa-label" style="min-width:80px;">资产类别</span><el-input v-model="form.category" placeholder="如 电子设备" /></div>
          </div>
        </div>
        <div class="fa-group" style="border-left-color:#e6a23c;">
          <div class="fa-group-header">
            <span class="fa-group-tag" style="background:#fdf6ec;color:#e6a23c;">财务参数</span>
          </div>
          <div class="fa-group-body">
            <div class="fa-field"><span class="fa-label" style="min-width:100px;">原值</span><el-input-number v-model="form.original_value" :min="0" :precision="2" style="width:100%" controls-position="right" /></div>
            <div class="fa-field"><span class="fa-label" style="min-width:100px;">残值率</span><el-input-number v-model="form.salvage_rate" :min="0" :max="1" :precision="2" :step="0.01" style="width:100%" controls-position="right" /></div>
            <div class="fa-field"><span class="fa-label" style="min-width:100px;">使用寿命</span><el-input-number v-model="form.useful_life" :min="1" style="width:100%" controls-position="right" /></div>
            <div class="fa-field"><span class="fa-label" style="min-width:100px;">折旧方法</span><el-select v-model="form.depreciation_method" style="width:100%"><el-option label="年限平均法" value="年限平均法" /></el-select></div>
          </div>
        </div>
        <div class="fa-group" style="border-left-color:#67c23a;">
          <div class="fa-group-header">
            <span class="fa-group-tag" style="background:#f0f9eb;color:#67c23a;">时间状态</span>
          </div>
          <div class="fa-group-body">
            <div class="fa-field"><span class="fa-label" style="min-width:100px;">开始折旧日</span><el-date-picker v-model="form.start_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width:100%" /></div>
            <div class="fa-field"><span class="fa-label" style="min-width:100px;">累计折旧</span><el-input-number v-model="form.accumulated_depreciation" :min="0" :precision="2" style="width:100%" controls-position="right" /></div>
            <div class="fa-field"><span class="fa-label" style="min-width:100px;">状态</span><el-select v-model="form.status" style="width:100%"><el-option label="在用" value="在用" /><el-option label="停用" value="停用" /><el-option label="报废" value="报废" /></el-select></div>
          </div>
        </div>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave">{{ isEdit ? '保存' : '确认入账' }}</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import fixedAssetsApi from '../api/fixedAssets'
import { formatMoney } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../api/index'

const list = ref([])
const loading = ref(false)
const statusFilter = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)

const defaultForm = () => ({
  asset_code: '', name: '', category: '', original_value: 0,
  salvage_rate: 0.05, useful_life: 12, depreciation_method: '年限平均法',
  start_date: new Date().toISOString().slice(0, 10),
  accumulated_depreciation: 0, status: '在用'
})
const form = ref(defaultForm())

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    const res = await fixedAssetsApi.getFixedAssets(params)
    list.value = res.items || res
  } catch (e) {
    handleError(e, { defaultMsg: '加载固定资产列表失败，请检查网络连接' })
  } finally {
    loading.value = false
  }
}

function showCreate() {
  isEdit.value = false
  editingId.value = null
  form.value = defaultForm()
  dialogVisible.value = true
}

function showEdit(row) {
  isEdit.value = true
  editingId.value = row.id
  form.value = { ...row }
  dialogVisible.value = true
}

async function handleSave() {
  try {
    if (isEdit.value) {
      await fixedAssetsApi.updateFixedAsset(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await fixedAssetsApi.createFixedAsset(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) {
    handleError(e, { defaultMsg: '保存固定资产失败，请检查输入数据是否正确' })
  }
}

async function handleDispose(row) {
  try {
    await fixedAssetsApi.disposeFixedAsset(row.id, '前端处置')
    ElMessage.success('资产已处置')
    loadData()
  } catch (e) {
    handleError(e, { defaultMsg: '处置固定资产失败，请检查该资产是否已处置' })
  }
}

function statusType(status) {
  const map = { '在用': 'success', '停用': 'warning', '报废': 'danger' }
  return map[status] || 'info'
}

useAccountAwareData(loadData)
</script>

<style scoped>
.fixed-assets-tab { padding: 0; }
.fa-group { background: #fafafa; border: 1px solid #f0f0f0; border-left: 4px solid; border-radius: 12px; overflow: hidden; margin-bottom: 16px; }
.fa-group-header { padding: 12px 16px 4px; }
.fa-group-tag { display: inline-block; padding: 2px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; letter-spacing: 0.5px; }
.fa-group-body { padding: 4px 16px 12px; display: flex; flex-direction: column; gap: 10px; }
.fa-field { display: flex; align-items: center; gap: 12px; }
.fa-label { font-size: 13px; color: #4e5969; flex-shrink: 0; }
</style>
