<template>
  <div>
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
        <el-table-column prop="asset_code" label="资产编码" width="130" />
        <el-table-column prop="name" label="资产名称" min-width="120" />
        <el-table-column prop="category" label="类别" width="100" align="center">
          <template #default="{ row }"><el-tag v-if="row.category" size="small">{{ row.category }}</el-tag><span v-else>-</span></template>
        </el-table-column>
        <el-table-column prop="original_value" label="原值" width="120" align="right"><template #default="{ row }"><span class="money">¥{{ formatMoney(row.original_value) }}</span></template></el-table-column>
        <el-table-column prop="salvage_rate" label="残值率" width="80" align="center"><template #default="{ row }">{{ (Number(row.salvage_rate) * 100).toFixed(0) }}%</template></el-table-column>
        <el-table-column prop="useful_life" label="使用寿命(月)" width="110" align="center" />
        <el-table-column prop="depreciation_method" label="折旧方法" width="110" align="center" />
        <el-table-column prop="start_date" label="开始日期" width="110" />
        <el-table-column prop="accumulated_depreciation" label="累计折旧" width="120" align="right"><template #default="{ row }"><span class="money">¥{{ formatMoney(row.accumulated_depreciation) }}</span></template></el-table-column>
        <el-table-column label="净值" width="120" align="right"><template #default="{ row }"><span class="money">¥{{ formatMoney(Number(row.original_value) - Number(row.accumulated_depreciation)) }}</span></template></el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center"><template #default="{ row }"><el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="showEdit(row)">编辑</el-button>
            <el-popconfirm title="确定删除此固定资产？" @confirm="handleDelete(row.id)"><template #reference><el-button size="small" link type="danger" style="margin-left:4px">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑固定资产' : '新增固定资产'" width="600px" destroy-on-close>
      <el-form :model="form" label-width="120px">
        <el-form-item label="资产编码" required><el-input v-model="form.asset_code" placeholder="如 FA-001" /></el-form-item>
        <el-form-item label="资产名称" required><el-input v-model="form.name" placeholder="如 办公电脑" /></el-form-item>
        <el-form-item label="资产类别"><el-input v-model="form.category" placeholder="如 电子设备" /></el-form-item>
        <el-form-item label="原值" required><el-input-number v-model="form.original_value" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="残值率"><el-input-number v-model="form.salvage_rate" :min="0" :max="1" :precision="2" :step="0.01" style="width:100%" /></el-form-item>
        <el-form-item label="使用寿命(月)" required><el-input-number v-model="form.useful_life" :min="1" style="width:100%" /></el-form-item>
        <el-form-item label="折旧方法"><el-select v-model="form.depreciation_method" style="width:100%"><el-option label="年限平均法" value="年限平均法" /></el-select></el-form-item>
        <el-form-item label="开始折旧日期" required><el-date-picker v-model="form.start_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="累计折旧"><el-input-number v-model="form.accumulated_depreciation" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="状态"><el-select v-model="form.status" style="width:100%"><el-option label="在用" value="在用" /><el-option label="停用" value="停用" /><el-option label="报废" value="报废" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave">{{ isEdit ? '保存' : '确认入账' }}</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import fixedAssetsApi from '../api/fixedAssets'
import { formatMoney } from '../api/common'
import { useAccountAwareData } from '../composables/useAccountAwareData'

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
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

function showCreate() {
  isEdit.value = false
  form.value = defaultForm()
  dialogVisible.value = true
}

function showEdit(row) {
  isEdit.value = true
  editingId.value = row.id
  form.value = {
    asset_code: row.asset_code || '', name: row.name || '', category: row.category || '',
    original_value: Number(row.original_value) || 0, salvage_rate: Number(row.salvage_rate) || 0.05,
    useful_life: Number(row.useful_life) || 12, depreciation_method: row.depreciation_method || '年限平均法',
    start_date: row.start_date || '', accumulated_depreciation: Number(row.accumulated_depreciation) || 0,
    status: row.status || '在用'
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.value.asset_code || !form.value.name || !form.value.start_date) {
    ElMessage.warning('请填写必填项')
    return
  }
  try {
    if (isEdit.value) {
      await fixedAssetsApi.updateFixedAsset(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await fixedAssetsApi.createFixedAsset(form.value)
      ElMessage.success('入账成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) {
    ElMessage.error('操作失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function handleDelete(id) {
  try {
    await fixedAssetsApi.deleteFixedAsset(id)
    ElMessage.success('已删除')
    loadData()
  } catch (e) {
    ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message))
  }
}

function statusType(s) {
  return s === '在用' ? 'success' : s === '停用' ? 'warning' : 'info'
}

useAccountAwareData(loadData)
</script>
