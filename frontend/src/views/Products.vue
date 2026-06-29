<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">商品列表</span>
          <div class="card-header-actions">
            <el-button type="primary" @click="showDialog(null)">
              <el-icon><Plus /></el-icon> 新增商品
            </el-button>
            <el-dropdown>
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
      <div class="filter-bar">
        <el-input v-model="search" placeholder="搜索名称/编码" clearable style="width:220px" @clear="loadData" @keyup.enter="loadData">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-input v-model="skuSearch" placeholder="SKU精确匹配" clearable style="width:160px" @clear="loadData" @keyup.enter="loadData" />
        <el-select v-model="categoryFilter" placeholder="分类筛选" clearable style="width:140px" @change="loadData">
          <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
        </el-select>
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>
      <el-table :data="list" stripe style="width:100%" v-loading="loading" @selection-change="handleSelectionChange">
        <template #empty>
          <el-empty description="暂无商品数据" />
        </template>
        <el-table-column type="selection" width="55" />
        <el-table-column prop="sku" label="编码" min-width="120" />
        <el-table-column prop="name" label="商品名称" min-width="160" />
        <el-table-column prop="category" label="分类" min-width="100" />
        <el-table-column prop="unit" label="单位" min-width="70" align="center" />
        <el-table-column prop="purchase_price" label="进价" min-width="110" align="right">
          <template #default="{ row }"><span class="money">¥{{ formatMoney(row.purchase_price) }}</span></template>
        </el-table-column>
        <el-table-column prop="sale_price" label="售价" min-width="110" align="right">
          <template #default="{ row }"><span class="money">¥{{ formatMoney(row.sale_price) }}</span></template>
        </el-table-column>
        <el-table-column label="库存" min-width="80" align="center">
          <template #default="{ row }">
            <span :class="{ 'negative-stock': row.current_stock < 0, 'alert-stock': row.current_stock >= 0 && row.current_stock < row.min_stock }">
              {{ row.current_stock ?? 0 }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="min_stock" label="预警线" min-width="80" align="center" />
        <el-table-column label="操作" width="120" fixed="right" align="center">
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
      <div class="pagination-bar">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next" @current-change="loadData" @size-change="loadData" />
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑商品' : '新增商品'" width="560px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="0">
        <div class="p-group" style="border-left-color:var(--primary);">
          <div class="p-group-header"><span class="p-group-tag" style="background:var(--primary-light);color:var(--primary);">基本信息</span></div>
          <div class="p-group-body">
            <div class="p-field"><span class="p-label" style="min-width:80px;">商品名称</span><el-input v-model="form.name" /></div>
            <div class="p-field"><span class="p-label" style="min-width:80px;">编码</span><el-input v-model="form.sku" /></div>
            <div class="p-field"><span class="p-label" style="min-width:80px;">分类</span><el-input v-model="form.category" /></div>
            <div class="p-field"><span class="p-label" style="min-width:80px;">单位</span><el-input v-model="form.unit" style="width:120px" /></div>
          </div>
        </div>
        <div class="p-group" style="border-left-color:var(--warning);">
          <div class="p-group-header"><span class="p-group-tag" style="background:var(--warning-light);color:var(--warning);">价格库存</span></div>
          <div class="p-group-body">
            <div class="p-field"><span class="p-label" style="min-width:80px;">进价</span><el-input-number v-model="form.purchase_price" :min="0" :precision="2" style="width:100%" controls-position="right" /></div>
            <div class="p-field"><span class="p-label" style="min-width:80px;">售价</span><el-input-number v-model="form.sale_price" :min="0" :precision="2" style="width:100%" controls-position="right" /></div>
            <div class="p-field"><span class="p-label" style="min-width:80px;">预警库存</span><el-input-number v-model="form.min_stock" :min="0" style="width:100%" controls-position="right" /></div>
            <div class="p-field"><span class="p-label" style="min-width:80px;">描述</span><el-input v-model="form.description" type="textarea" :rows="2" /></div>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import productsApi from '../api/products'
import exportApi from '../api/export'
import { formatMoney } from '../utils/format'
import { handleError } from '../api/index'
import { useAccountAwareData } from '../composables/useAccountAwareData'

const list = ref([])
const loading = ref(false)
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
const formRef = ref(null)
const form = ref({ name: '', sku: '', category: '', unit: '个', purchase_price: 0, sale_price: 0, min_stock: 0, description: '' })
const formRules = {
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  sku: [{ required: true, message: '请输入商品编码', trigger: 'blur' }]
}

const loadData = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value) params.search = search.value
    if (skuSearch.value) params.sku = skuSearch.value
    if (categoryFilter.value) params.category = categoryFilter.value
    const res = await productsApi.getProducts(params)
    total.value = res.total
    list.value = res.items
  } catch (e) { handleError(e, { defaultMsg: '加载商品列表失败，请检查网络连接' }) }
  finally { loading.value = false }
}

const loadCategories = async () => {
  try { categories.value = await productsApi.getCategories() } catch (e) { /* ignore */ }
}

const showDialog = (row) => {
  if (row) {
    editingId.value = row.id
    form.value = {
      ...row,
      purchase_price: Number(row.purchase_price) || 0,
      sale_price: Number(row.sale_price) || 0,
      min_stock: Number(row.min_stock) || 0,
    }
  } else {
    editingId.value = null
    form.value = { name: '', sku: '', category: '', unit: '个', purchase_price: 0, sale_price: 0, min_stock: 0, description: '' }
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    if (editingId.value) {
      await productsApi.updateProduct(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await productsApi.createProduct(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) { handleError(e, { defaultMsg: '保存失败，请检查输入数据是否正确' }) }
}

const handleDelete = async (id) => {
  try { await productsApi.deleteProduct(id); ElMessage.success('已删除'); loadData() }
  catch (e) { handleError(e, { defaultMsg: '删除失败，请检查该商品是否已被其他单据引用' }) }
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
    await exportApi.exportProductsBatch(ids, format)
    ElMessage.success('导出成功')
  } catch (e) {
    handleError(e, { defaultMsg: '导出失败，请检查文件权限和磁盘空间' })
  }
}

useAccountAwareData(loadData)
loadCategories()
</script>

<style scoped>
.p-group { background: var(--bg-elevated); border: 1px solid var(--border-lighter); border-left: 4px solid; border-radius: 12px; overflow: hidden; margin-bottom: 16px; }
.p-group-header { padding: 12px 16px 4px; }
.p-group-tag { display: inline-block; padding: 2px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; letter-spacing: 0.5px; }
.p-group-body { padding: 4px 16px 12px; display: flex; flex-direction: column; gap: 10px; }
.p-field { display: flex; align-items: center; gap: 12px; }
.p-label { font-size: 13px; color: var(--text-regular); flex-shrink: 0; }
</style>