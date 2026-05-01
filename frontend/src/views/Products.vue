<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-weight:600;">商品列表</span>
          <div>
            <el-button type="primary" @click="showDialog(null)">
              <el-icon><Plus /></el-icon> 新增商品
            </el-button>
            <el-dropdown style="margin-left:8px;">
              <el-button :disabled="selectedRows.length === 0"><el-icon><Download /></el-icon> 批量导出</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :disabled="selectedRows.length === 0" @click="exportBatch('excel')">Excel</el-dropdown-item>
                  <el-dropdown-item :disabled="selectedRows.length === 0" @click="exportBatch('csv')">CSV</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </template>
      <div style="margin-bottom:12px;display:flex;gap:12px;">
        <el-input v-model="search" placeholder="搜索名称/编码（模糊）" clearable style="width:240px" @clear="loadData" @keyup.enter="loadData">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-input v-model="skuSearch" placeholder="SKU精确匹配" clearable style="width:160px" @clear="loadData" @keyup.enter="loadData" />
        <el-select v-model="categoryFilter" placeholder="分类筛选" clearable style="width:140px" @change="loadData">
          <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
        </el-select>
        <el-button @click="loadData">查询</el-button>
      </div>
      <el-table :data="list" stripe style="width:100%" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="sku" label="编码" width="110" />
        <el-table-column prop="name" label="商品名称" min-width="140" />
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column prop="unit" label="单位" width="70" />
        <el-table-column prop="purchase_price" label="进价" width="90">
          <template #default="{ row }">¥{{ row.purchase_price?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="sale_price" label="售价" width="90">
          <template #default="{ row }">¥{{ row.sale_price?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="库存" width="80">
          <template #default="{ row }">
            <span :class="{ 'negative-stock': row.current_stock < 0, 'alert-stock': row.current_stock >= 0 && row.current_stock < row.min_stock }">
              {{ row.current_stock ?? 0 }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="min_stock" label="预警线" width="80" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="showDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除?" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button size="small" link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div style="display:flex;justify-content:flex-end;margin-top:16px;">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next" @current-change="loadData" @size-change="loadData" />
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑商品' : '新增商品'" width="500px" destroy-on-close>
      <el-form :model="form" label-width="80px" style="padding-right:20px;">
        <el-form-item label="商品名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="编码" required>
          <el-input v-model="form.sku" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="form.category" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="form.unit" style="width:120px" />
        </el-form-item>
        <el-form-item label="进价">
          <el-input-number v-model="form.purchase_price" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="售价">
          <el-input-number v-model="form.sale_price" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="预警库存">
          <el-input-number v-model="form.min_stock" :min="0" style="width:100%" />
        </el-form-item>
        <el-form-item v-if="!editingId" label="初始库存">
          <el-input-number v-model="form.initial_stock" :min="0" style="width:100%" />
        </el-form-item>
        <el-form-item v-if="form.initial_stock > 0 && form.initial_stock < form.min_stock" label="">
          <el-alert type="warning" :closable="false" show-icon title="初始库存低于预警线" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
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
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const categories = ref([])
const search = ref('')
const skuSearch = ref('')
const categoryFilter = ref('')
const dialogVisible = ref(false)
const editingId = ref(null)
const selectedRows = ref([])
const form = ref({ name: '', sku: '', category: '', unit: '个', purchase_price: 0, sale_price: 0, min_stock: 0, description: '' })

const loadData = async () => {
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value) params.search = search.value
    if (skuSearch.value) params.sku = skuSearch.value
    if (categoryFilter.value) params.category = categoryFilter.value
    const res = await api.getProducts(params)
    total.value = res.total
    list.value = res.items
  } catch (e) { ElMessage.error('加载失败') }
}

const loadCategories = async () => {
  try { categories.value = await api.getCategories() } catch (e) { /* ignore */ }
}

const showDialog = (row) => {
  if (row) {
    editingId.value = row.id
    form.value = { ...row }
  } else {
    editingId.value = null
    form.value = { name: '', sku: '', category: '', unit: '个', purchase_price: 0, sale_price: 0, min_stock: 0, initial_stock: 0, description: '' }
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (editingId.value) {
      await api.updateProduct(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await api.createProduct(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) { ElMessage.error('保存失败') }
}

const handleDelete = async (id) => {
  try { await api.deleteProduct(id); ElMessage.success('已删除'); loadData() }
  catch (e) { ElMessage.error('删除失败') }
}

const handleSelectionChange = (rows) => {
  selectedRows.value = rows
}

const exportBatch = async (format) => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要导出的商品')
    return
  }
  try {
    const ids = selectedRows.value.map(r => r.id)
    console.log('[exportBatch] 准备导出:', ids, format)
    await api.exportProductsBatch(ids, format)
    ElMessage.success('导出成功')
  } catch (e) {
    console.error('[exportBatch] 导出失败:', e)
    const detail = e.response?.data?.detail || e.message || '未知错误'
    ElMessage.error('导出失败: ' + detail)
  }
}

onMounted(() => { loadData(); loadCategories() })
</script>