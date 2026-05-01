<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-weight:600;">采购记录</span>
          <div>
            <el-button type="primary" @click="showDialog()"><el-icon><Plus /></el-icon> 新建采购</el-button>
            <el-dropdown style="margin-left:8px;">
              <el-button><el-icon><Download /></el-icon> 导出</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="exportData('excel')">Excel</el-dropdown-item>
                  <el-dropdown-item @click="exportData('csv')">CSV</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </template>
      <div style="margin-bottom:12px;display:flex;gap:12px;flex-wrap:wrap;">
        <el-input v-model="keyword" placeholder="搜索单号/供应商/项目" clearable style="width:220px" @clear="loadData" @keyup.enter="loadData">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" />
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width:120px">
          <el-option label="已完成" value="completed" />
          <el-option label="待处理" value="pending" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
        <el-button type="primary" @click="loadData"><el-icon><Search /></el-icon> 查询</el-button>
      </div>
      <el-table :data="list" stripe style="width:100%" @expand-change="onExpand">
        <el-table-column type="expand" width="40">
          <template #default="{ row }">
            <div style="padding: 8px 24px;">
              <el-table :data="row.items" size="small" :border="true" style="width:100%">
                <el-table-column prop="product_name" label="商品" min-width="120" />
                <el-table-column prop="quantity" label="数量" width="80" />
                <el-table-column prop="unit_price" label="单价" width="90">
                  <template #default="{ row: item }">¥{{ item.unit_price?.toFixed(2) }}</template>
                </el-table-column>
                <el-table-column prop="total_price" label="小计" width="100">
                  <template #default="{ row: item }">¥{{ item.total_price?.toFixed(2) }}</template>
                </el-table-column>
              </el-table>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="order_no" label="单号" width="150" />
        <el-table-column prop="supplier_name" label="供应商" width="120" />
        <el-table-column prop="project_name" label="项目" width="150" />
        <el-table-column label="商品数" width="80">
          <template #default="{ row }">{{ row.items?.length || 0 }}</template>
        </el-table-column>
        <el-table-column prop="total_price" label="总价" width="100">
          <template #default="{ row }">¥{{ row.total_price?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="has_invoice" label="已开票" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.has_invoice ? 'success' : 'info'" size="small">
              {{ row.has_invoice ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="payment_method" label="支付方式" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.payment_method === 'company' ? 'primary' : 'warning'" size="small">
              {{ row.payment_method === 'company' ? '公司' : '个人垫付' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="payment_status" label="付款状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.payment_status === 'paid' ? 'success' : 'warning'" size="small">
              {{ row.payment_status === 'paid' ? '已付款' : '未付款' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'cancelled' ? 'danger' : 'warning'" size="small">
              {{ row.status === 'completed' ? '已完成' : row.status === 'cancelled' ? '已取消' : '待处理' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="purchase_date" label="日期" width="110">
          <template #default="{ row }">{{ row.purchase_date?.slice(0, 10) }}</template>
        </el-table-column>
        <el-table-column prop="notes" label="备注" min-width="100" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="showEditDialog(row)">编辑</el-button>
            <el-dropdown v-if="row.status === 'pending'" style="margin-left:4px;">
              <el-button size="small" link type="primary">状态<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="changeStatus(row.id, 'completed')">完成</el-dropdown-item>
                  <el-dropdown-item @click="changeStatus(row.id, 'cancelled')">取消</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-dropdown v-else-if="row.status === 'completed'" style="margin-left:4px;">
              <el-button size="small" link type="primary">状态<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="changeStatus(row.id, 'cancelled')">取消(退回库存)</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-popconfirm title="确定删除此采购单？删除后将扣减对应库存" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button size="small" link type="danger" style="margin-left:4px">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div style="display:flex;justify-content:flex-end;margin-top:16px;">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next" @current-change="loadData" @size-change="loadData" />
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新建采购单" width="680px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="供应商">
          <el-select v-model="form.supplier_id" filterable clearable placeholder="选择供应商" style="width:100%">
            <el-option v-for="s in suppliers" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目">
          <el-select v-model="form.project_id" filterable clearable placeholder="选择项目(可空)" style="width:100%">
            <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="税率">
          <el-select v-model="form.tax_rate" style="width:100%">
            <el-option label="0%" :value="0" />
            <el-option label="3%" :value="0.03" />
            <el-option label="6%" :value="0.06" />
            <el-option label="9%" :value="0.09" />
            <el-option label="13%" :value="0.13" />
          </el-select>
        </el-form-item>
        <el-form-item label="是否开票">
          <el-switch v-model="form.has_invoice" />
        </el-form-item>
        <el-form-item label="支付方式">
          <el-select v-model="form.payment_method" style="width:100%">
            <el-option label="公司" value="company" />
            <el-option label="个人垫付" value="private_advance" />
          </el-select>
        </el-form-item>
        <el-form-item label="付款状态">
          <el-select v-model="form.payment_status" style="width:100%">
            <el-option label="未付款" value="unpaid" />
            <el-option label="已付款" value="paid" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="附件图片">
          <ImageUpload v-model="form.image_url" business-type="purchase" :record-id="editingId || 0" :update-api="api.updatePurchase" />
        </el-form-item>
      </el-form>

      <div style="margin-bottom:8px;font-weight:600;">采购明细</div>
      <el-table :data="form.items" size="small" :border="true" style="width:100%">
        <el-table-column label="商品" min-width="160">
          <template #default="{ row, $index }">
            <el-select v-model="row.product_id" filterable placeholder="选择商品" size="small" style="width:100%" @change="onItemProductChange($index)">
              <el-option v-for="p in products" :key="p.id" :label="`${p.name} (${p.sku})`" :value="p.id" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="100">
          <template #default="{ row }">
            <el-input-number v-model="row.quantity" :min="1" size="small" style="width:90px" />
          </template>
        </el-table-column>
        <el-table-column label="单价" width="120">
          <template #default="{ row }">
            <el-input-number v-model="row.unit_price" :min="0" :precision="2" size="small" style="width:110px" />
          </template>
        </el-table-column>
        <el-table-column label="小计" width="100">
          <template #default="{ row }">¥{{ (row.quantity * row.unit_price).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="60">
          <template #default="{ $index }">
            <el-button size="small" link type="danger" @click="removeItem($index)"><el-icon><Delete /></el-icon></el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top:8px;">
        <el-button size="small" @click="addItem"><el-icon><Plus /></el-icon> 添加商品</el-button>
        <span style="float:right;font-size:16px;font-weight:600;color:var(--primary);">订单总额: ¥{{ orderTotal.toFixed(2) }}</span>
      </div>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">确认采购(自动入库)</el-button>
      </template>
    </el-dialog>

    <!-- 编辑采购单弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑采购单" width="680px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="供应商">
          <el-select v-model="editForm.supplier_id" filterable clearable placeholder="选择供应商" style="width:100%">
            <el-option v-for="s in suppliers" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目">
          <el-select v-model="editForm.project_id" filterable clearable placeholder="选择项目(可空)" style="width:100%">
            <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="税率">
          <el-select v-model="editForm.tax_rate" style="width:100%">
            <el-option label="0%" :value="0" />
            <el-option label="3%" :value="0.03" />
            <el-option label="6%" :value="0.06" />
            <el-option label="9%" :value="0.09" />
            <el-option label="13%" :value="0.13" />
          </el-select>
        </el-form-item>
        <el-form-item label="是否开票">
          <el-switch v-model="editForm.has_invoice" />
        </el-form-item>
        <el-form-item label="支付方式">
          <el-select v-model="editForm.payment_method" style="width:100%">
            <el-option label="公司" value="company" />
            <el-option label="个人垫付" value="private_advance" />
          </el-select>
        </el-form-item>
        <el-form-item label="付款状态">
          <el-select v-model="editForm.payment_status" style="width:100%">
            <el-option label="未付款" value="unpaid" />
            <el-option label="已付款" value="paid" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.notes" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="附件图片">
          <ImageUpload v-model="editForm.image_url" business-type="purchase" :record-id="editingId || 0" :update-api="api.updatePurchase" />
        </el-form-item>
      </el-form>

      <div style="margin-bottom:8px;font-weight:600;">采购明细（修改后保存将重新计算库存）</div>
      <el-table :data="editForm.items" size="small" :border="true" style="width:100%">
        <el-table-column label="商品" min-width="160">
          <template #default="{ row, $index }">
            <el-select v-model="row.product_id" filterable placeholder="选择商品" size="small" style="width:100%" @change="onEditItemProductChange($index)">
              <el-option v-for="p in products" :key="p.id" :label="`${p.name} (${p.sku})`" :value="p.id" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="100">
          <template #default="{ row }">
            <el-input-number v-model="row.quantity" :min="1" size="small" style="width:90px" />
          </template>
        </el-table-column>
        <el-table-column label="单价" width="120">
          <template #default="{ row }">
            <el-input-number v-model="row.unit_price" :min="0" :precision="2" size="small" style="width:110px" />
          </template>
        </el-table-column>
        <el-table-column label="小计" width="100">
          <template #default="{ row }">¥{{ (row.quantity * row.unit_price).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="60">
          <template #default="{ $index }">
            <el-button size="small" link type="danger" @click="removeEditItem($index)"><el-icon><Delete /></el-icon></el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top:8px;">
        <el-button size="small" @click="addEditItem"><el-icon><Plus /></el-icon> 添加商品</el-button>
        <span style="float:right;font-size:16px;font-weight:600;color:var(--primary);">订单总额: ¥{{ editOrderTotal.toFixed(2) }}</span>
      </div>
      <div v-if="editForm.items.length === 0" style="margin-top:8px;color:#f56c6c;font-size:12px;">
        <el-icon><Warning /></el-icon> 删除所有商品后保存将自动删除此采购单
      </div>

      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEditSave">保存修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import { resolveImageUrl } from '../api'
import ImageUpload from '../components/ImageUpload.vue'

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const products = ref([])
const suppliers = ref([])
const projectList = ref([])
const dateRange = ref(null)
const statusFilter = ref('')
const keyword = ref('')
const dialogVisible = ref(false)
const form = ref({ supplier_id: null, project_id: null, tax_rate: 0.03, has_invoice: false, payment_method: 'company', payment_status: 'unpaid', notes: '', image_url: '', items: [] })

const orderTotal = computed(() => form.value.items.reduce((sum, item) => sum + (item.quantity * item.unit_price), 0))

// 编辑相关
const editDialogVisible = ref(false)
const editingId = ref(null)
const editForm = ref({ supplier_id: null, project_id: null, has_invoice: false, payment_method: 'company', notes: '', image_url: '', items: [] })
const editOrderTotal = computed(() => editForm.value.items.reduce((sum, item) => sum + (item.quantity * item.unit_price), 0))

const loadData = async () => {
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (keyword.value) params.keyword = keyword.value
    if (dateRange.value) { params.start_date = dateRange.value[0]; params.end_date = dateRange.value[1] }
    if (statusFilter.value) params.status = statusFilter.value
    const res = await api.getPurchases(params)
    total.value = res.total
    list.value = res.items
  } catch (e) { ElMessage.error('加载失败') }
}

const loadOptions = async () => {
  try {
    const [pRes, sRes, projRes] = await Promise.all([
      api.getProducts({ page: 1, page_size: 1000 }),
      api.getSuppliers({ page: 1, page_size: 1000 }),
      api.getProjectList()
    ])
    products.value = pRes.items || pRes
    suppliers.value = sRes.items || sRes
    projectList.value = projRes.items || projRes
  } catch (e) { /* ignore */ }
}

const addItem = () => {
  form.value.items.push({ product_id: null, quantity: 1, unit_price: 0 })
}

const removeItem = (idx) => {
  form.value.items.splice(idx, 1)
}

const onItemProductChange = (idx) => {
  const item = form.value.items[idx]
  const p = products.value.find(x => x.id === item.product_id)
  if (p) item.unit_price = p.purchase_price
  // ★ 防重：如果选的商品已存在于其他行，提示并清空
  if (item.product_id) {
    const dupIdx = form.value.items.findIndex((it, i) => i !== idx && it.product_id === item.product_id)
    if (dupIdx !== -1) {
      const prodName = p?.name || `ID=${item.product_id}`
      ElMessage.warning(`商品"${prodName}"已在第${dupIdx + 1}行，请直接修改数量`)
      item.product_id = null
    }
  }
}

const showDialog = () => {
  form.value = { supplier_id: null, project_id: null, tax_rate: 0.03, has_invoice: false, payment_method: 'company', payment_status: 'unpaid', notes: '', items: [{ product_id: null, quantity: 1, unit_price: 0 }] }
  dialogVisible.value = true
  loadOptions()
}

const handleSave = async () => {
  const validItems = form.value.items.filter(i => i.product_id && i.quantity > 0)
  if (validItems.length === 0) { ElMessage.warning('请至少添加一个有效商品'); return }
  try {
    await api.createPurchase({
      supplier_id: form.value.supplier_id,
      project_id: form.value.project_id,
      tax_rate: form.value.tax_rate,
      has_invoice: form.value.has_invoice,
      payment_method: form.value.payment_method,
      payment_status: form.value.payment_status,
      notes: form.value.notes,
      items: validItems.map(i => ({ product_id: i.product_id, quantity: i.quantity, unit_price: i.unit_price }))
    })
    ElMessage.success('采购成功，已自动入库')
    dialogVisible.value = false
    loadData()
  } catch (e) { ElMessage.error('采购失败') }
}

const changeStatus = async (id, status) => {
  try {
    await api.updatePurchase(id, { status })
    ElMessage.success('状态已更新')
    loadData()
  } catch (e) { ElMessage.error('更新失败') }
}

const handleDelete = async (id) => {
  try {
    await api.deletePurchase(id)
    ElMessage.success('已删除')
    loadData()
  } catch (e) { ElMessage.error('删除失败') }
}

const showEditDialog = (row) => {
  editingId.value = row.id
  editForm.value = {
    supplier_id: row.supplier_id,
    project_id: row.project_id,
    tax_rate: row.tax_rate || 0.13,
    has_invoice: row.has_invoice,
    payment_method: row.payment_method,
    payment_status: row.payment_status || 'unpaid',
    notes: row.notes || '',
    image_url: row.image_url || '',
    items: row.items.map(item => ({
      product_id: item.product_id,
      quantity: item.quantity,
      unit_price: item.unit_price
    }))
  }
  editDialogVisible.value = true
  loadOptions()
}

const onEditItemProductChange = (idx) => {
  const item = editForm.value.items[idx]
  const p = products.value.find(x => x.id === item.product_id)
  if (p) item.unit_price = p.purchase_price
  // ★ 防重：如果选的商品已存在于其他行，提示并清空
  if (item.product_id) {
    const dupIdx = editForm.value.items.findIndex((it, i) => i !== idx && it.product_id === item.product_id)
    if (dupIdx !== -1) {
      const prodName = p?.name || `ID=${item.product_id}`
      ElMessage.warning(`商品"${prodName}"已在第${dupIdx + 1}行，请直接修改数量`)
      item.product_id = null
    }
  }
}

const addEditItem = () => {
  editForm.value.items.push({ product_id: null, quantity: 1, unit_price: 0 })
}

const removeEditItem = (idx) => {
  editForm.value.items.splice(idx, 1)
}

const handleEditSave = async () => {
  const validItems = editForm.value.items.filter(i => i.product_id && i.quantity > 0)
  // 如果用户删光了所有行，也允许提交（后端会删除整个采购单）
  try {
    await api.updatePurchase(editingId.value, {
      supplier_id: editForm.value.supplier_id,
      project_id: editForm.value.project_id,
      tax_rate: editForm.value.tax_rate,
      has_invoice: editForm.value.has_invoice,
      payment_method: editForm.value.payment_method,
      payment_status: editForm.value.payment_status,
      notes: editForm.value.notes,
      image_url: editForm.value.image_url,
      items: validItems.map(i => ({ product_id: i.product_id, quantity: i.quantity, unit_price: i.unit_price }))
    })
    if (validItems.length === 0) {
      ElMessage.success('采购单已删除（商品行数归零）')
    } else {
      ElMessage.success('采购单修改成功，库存已自动调整')
    }
    editDialogVisible.value = false
    loadData()
  } catch (e) { ElMessage.error('修改失败: ' + (e.response?.data?.detail || e.message)) }
}

const exportData = async (format) => {
  try {
    const params = {}
    if (keyword.value) params.keyword = keyword.value
    if (dateRange.value) { params.start_date = dateRange.value[0]; params.end_date = dateRange.value[1] }
    if (statusFilter.value) params.status = statusFilter.value
    await api.exportFile('purchases', format, params)
  } catch (e) { ElMessage.error('导出失败') }
}

const onExpand = (row, expandedRows) => {
  // trigger lazy load if needed
}

onMounted(loadData)
</script>