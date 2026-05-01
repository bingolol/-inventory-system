<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-weight:600;">供应商列表</span>
          <el-button type="primary" @click="showDialog(null)"><el-icon><Plus /></el-icon> 新增供应商</el-button>
        </div>
      </template>
      <div style="margin-bottom:12px;">
        <el-input v-model="search" placeholder="搜索供应商名称" clearable style="width:240px" @clear="loadData" @keyup.enter="loadData">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button @click="loadData" style="margin-left:8px;">查询</el-button>
      </div>
      <el-table :data="list" stripe style="width:100%">
        <el-table-column prop="name" label="供应商名称" min-width="140" />
        <el-table-column prop="contact" label="联系人" width="120" />
        <el-table-column prop="phone" label="电话" width="140" />
        <el-table-column prop="address" label="地址" min-width="180" />
        <el-table-column prop="notes" label="备注" min-width="120" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="showDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除?" @confirm="handleDelete(row.id)">
              <template #reference><el-button size="small" link type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div style="display:flex;justify-content:flex-end;margin-top:16px;">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next" @current-change="loadData" @size-change="loadData" />
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑供应商' : '新增供应商'" width="500px" destroy-on-close>
      <el-form :model="form" label-width="80px" style="padding-right:20px;">
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="联系人"><el-input v-model="form.contact" /></el-form-item>
        <el-form-item label="电话"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="地址"><el-input v-model="form.address" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.notes" type="textarea" :rows="2" /></el-form-item>
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
const search = ref('')
const dialogVisible = ref(false)
const editingId = ref(null)
const defaultForm = () => ({ name: '', contact: '', phone: '', address: '', notes: '' })
const form = ref(defaultForm())

const loadData = async () => {
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value) params.search = search.value
    const res = await api.getSuppliers(params)
    total.value = res.total
    list.value = res.items
  } catch (e) { ElMessage.error('加载失败') }
}

const showDialog = (row) => {
  editingId.value = row ? row.id : null
  form.value = row ? { ...row } : defaultForm()
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (editingId.value) { await api.updateSupplier(editingId.value, form.value); ElMessage.success('更新成功') }
    else { await api.createSupplier(form.value); ElMessage.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch (e) { ElMessage.error('保存失败') }
}

const handleDelete = async (id) => {
  try { await api.deleteSupplier(id); ElMessage.success('已删除'); loadData() }
  catch (e) { ElMessage.error('删除失败') }
}

onMounted(loadData)
</script>