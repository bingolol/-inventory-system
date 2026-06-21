<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">{{ title }}</span>
          <el-button type="primary" @click="showDialog(null)"><el-icon><Plus /></el-icon> {{ addLabel }}</el-button>
        </div>
      </template>
      <div class="filter-bar">
        <el-input v-model="search" :placeholder="searchPlaceholder" clearable style="width:220px" @clear="loadData" @keyup.enter="loadData">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>
      <el-table :data="list" stripe style="width:100%">
        <el-table-column prop="name" :label="nameLabel" min-width="140" />
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
      <div class="pagination-bar">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next" @current-change="loadData" @size-change="loadData" />
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? editTitle : addTitle" width="500px" destroy-on-close>
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
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../api/index'

const props = defineProps({
  title: { type: String, required: true },
  searchPlaceholder: { type: String, default: '搜索名称' },
  nameLabel: { type: String, default: '名称' },
  addLabel: { type: String, default: '新增' },
  addTitle: { type: String, default: '新增' },
  editTitle: { type: String, default: '编辑' },
  api: { type: Object, required: true }
})

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
    const res = await props.api.getList(params)
    total.value = res.total
    list.value = res.items
  } catch (e) { handleError(e, { defaultMsg: '加载失败' }) }
}

const showDialog = (row) => {
  editingId.value = row ? row.id : null
  form.value = row ? { ...row } : defaultForm()
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (editingId.value) {
      await props.api.update(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await props.api.create(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) { handleError(e, { defaultMsg: '保存失败' }) }
}

const handleDelete = async (id) => {
  try {
    await props.api.delete(id)
    ElMessage.success('已删除')
    loadData()
  } catch (e) { handleError(e, { defaultMsg: '删除失败' }) }
}

useAccountAwareData(loadData)
</script>
