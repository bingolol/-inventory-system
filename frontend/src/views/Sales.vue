<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-weight:600;">销售记录</span>
          <div>
            <el-button type="primary" @click="showDialog()"><el-icon><Plus /></el-icon> 新建销售</el-button>
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
        <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="loadData" />
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width:120px" @change="loadData">
          <el-option label="已完成" value="completed" />
          <el-option label="待处理" value="pending" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
      </div>
      <el-table :data="list" stripe style="width:100%">
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
        <el-table-column prop="customer_name" label="客户" width="120" />
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
        <el-table-column prop="payment_status" label="支付状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.payment_status === 'paid' ? 'success' : 'warning'" size="small">
              {{ row.payment_status === 'paid' ? '已支付' : '未支付' }}
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
        <el-table-column prop="sale_date" label="日期" width="110">
          <template #default="{ row }">{{ row.sale_date?.slice(0, 10) }}</template>
        </el-table-column>
        <el-table-column prop="notes" label="备注" min-width="100" />
        <el-table-column label="附件" width="70" align="center">
          <template #default="{ row }">
            <el-image v-if="row.image_url" :src="resolveImageUrl(row.image_url)" style="width:36px;height:36px;border-radius:4px;" fit="cover" :preview-src-list="[resolveImageUrl(row.image_url)]" preview-teleported />
            <span v-else style="color:#999;font-size:12px;">无</span>
          </template>
        </el-table-column>
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
            <el-popconfirm title="确定删除此销售单？" @confirm="handleDelete(row.id)">
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

    <el-dialog v-model="dialogVisible" title="新建销售单" width="680px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="客户">
          <el-select v-model="form.customer_name" filterable allow-create default-first-option clearable placeholder="选择或输入客户名(可空=散客)" style="width:100%">
            <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目">
          <el-select v-model="form.project_id" filterable clearable placeholder="选择项目(可空)" style="width:100%">
            <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="出库">
          <el-switch
            v-model="form.deduct_inventory"
            :disabled="!!form.project_id"
            active-text="零售出库(直接扣库存)"
            inactive-text="不扣库存"
          />
          <span v-if="form.project_id" style="color:#999;font-size:12px;margin-left:8px;">
            项目业务库存走领料，销售单不扣库存
          </span>
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
        <el-form-item label="支付状态">
          <el-select v-model="form.payment_status" style="width:100%">
            <el-option label="未支付" value="unpaid" />
            <el-option label="已支付" value="paid" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="附件图片">
          <ImageUpload v-model="form.image_url" business-type="sale" :record-id="form.id || 0" :update-api="(data) => api.updateSale(form.id, data)" />
        </el-form-item>
      </el-form>

      <div style="margin-bottom:8px;font-weight:600;">销售明细</div>
      <el-table :data="form.items" size="small" :border="true" style="width:100%">
        <el-table-column label="商品" min-width="160">
          <template #default="{ row, $index }">
            <el-select v-model="row.product_id" filterable placeholder="选择商品" size="small" style="width:100%" @change="onItemProductChange($index)">
              <el-option v-for="p in products" :key="p.id" :label="`${p.name} (${p.sku}) 库存:${p.current_stock ?? 0}`" :value="p.id" />
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
        <div style="float:right;display:flex;align-items:center;gap:8px;">
          <span style="font-size:14px;color:#999;">明细合计: ¥{{ orderTotal.toFixed(2) }}</span>
          <span style="font-size:14px;color:#999;">→</span>
          <el-input-number v-model="form.total_price" :precision="2" :min="0" size="small" placeholder="自定义金额" style="width:130px;" />
          <span style="font-size:16px;font-weight:600;color:var(--primary);">订单总额: ¥{{ (form.total_price ?? orderTotal).toFixed(2) }}</span>
        </div>
      </div>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">确认销售</el-button>
      </template>
    </el-dialog>

    <!-- 编辑销售单弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑销售单" width="680px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="客户">
          <el-select v-model="editForm.customer_name" filterable allow-create default-first-option clearable placeholder="选择或输入客户名(可空=散客)" style="width:100%">
            <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目">
          <el-select v-model="editForm.project_id" filterable clearable placeholder="选择项目(可空)" style="width:100%">
            <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="出库">
          <el-switch
            v-model="editForm.deduct_inventory"
            :disabled="!!editForm.project_id"
            active-text="零售出库(直接扣库存)"
            inactive-text="不扣库存"
          />
          <span v-if="editForm.project_id" style="color:#999;font-size:12px;margin-left:8px;">
            项目业务库存走领料，销售单不扣库存
          </span>
        </el-form-item>
        <el-form-item label="是否开票">
          <el-switch v-model="editForm.has_invoice" />
        </el-form-item>
        <el-form-item label="支付状态">
          <el-select v-model="editForm.payment_status" style="width:100%">
            <el-option label="未支付" value="unpaid" />
            <el-option label="已支付" value="paid" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.notes" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="附件图片">
          <ImageUpload v-model="editForm.image_url" business-type="sale" :record-id="editForm.id || 0" :update-api="(data) => api.updateSale(editForm.id, data)" />
        </el-form-item>
      </el-form>

      <div style="margin-bottom:8px;font-weight:600;">销售明细（修改后保存将重新计算库存/收入）</div>
      <el-table :data="editForm.items" size="small" :border="true" style="width:100%">
        <el-table-column label="商品" min-width="160">
          <template #default="{ row, $index }">
            <el-select v-model="row.product_id" filterable placeholder="选择商品" size="small" style="width:100%" @change="onEditItemProductChange($index)">
              <el-option v-for="p in products" :key="p.id" :label="`${p.name} (${p.sku}) 库存:${p.current_stock ?? 0}`" :value="p.id" />
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
        <div style="float:right;display:flex;align-items:center;gap:8px;">
          <span style="font-size:14px;color:#999;">明细合计: ¥{{ editOrderTotal.toFixed(2) }}</span>
          <span style="font-size:14px;color:#999;">→</span>
          <el-input-number v-model="editForm.total_price" :precision="2" :min="0" size="small" placeholder="自定义金额" style="width:130px;" />
          <span style="font-size:16px;font-weight:600;color:var(--primary);">订单总额: ¥{{ (editForm.total_price ?? editOrderTotal).toFixed(2) }}</span>
        </div>
      </div>
      <div v-if="editForm.items.length === 0" style="margin-top:8px;color:#f56c6c;font-size:12px;">
        <el-icon><Warning /></el-icon> 删除所有商品后保存将自动删除此销售单
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
const customers = ref([])
const projectList = ref([])
const dateRange = ref(null)
const statusFilter = ref('')
const dialogVisible = ref(false)
const form = ref({ id: null, customer_name: '', project_id: null, deduct_inventory: false, tax_rate: 0.03, has_invoice: false, payment_status: 'unpaid', notes: '', image_url: '', total_price: null, items: [] })

const orderTotal = computed(() => form.value.items.reduce((sum, item) => sum + (item.quantity * item.unit_price), 0))

// 编辑相关
const editDialogVisible = ref(false)
const editForm = ref({ id: null, customer_name: '', project_id: null, deduct_inventory: false, has_invoice: false, payment_status: 'unpaid', notes: '', image_url: '', total_price: null, items: [] })
const editOrderTotal = computed(() => editForm.value.items.reduce((sum, item) => sum + (item.quantity * item.unit_price), 0))

const loadData = async () => {
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (dateRange.value) { params.start_date = dateRange.value[0]; params.end_date = dateRange.value[1] }
    if (statusFilter.value) params.status = statusFilter.value
    const res = await api.getSales(params)
    total.value = res.total
    list.value = res.items
  } catch (e) { ElMessage.error('加载失败') }
}

const loadOptions = async () => {
  try {
    const [pRes, cRes, projRes] = await Promise.all([
      api.getProducts({ page: 1, page_size: 1000 }),
      api.getCustomers({ page: 1, page_size: 1000 }),
      api.getProjectList()
    ])
    products.value = pRes.items || pRes
    customers.value = cRes.items || cRes
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
  // 销售单价由用户自行填写，不自动带商品指导价
  // ★ 防重：如果选的商品已存在于其他行，提示并清空
  const currentProductId = form.value.items[idx].product_id
  if (currentProductId) {
    const dupIdx = form.value.items.findIndex((item, i) => i !== idx && item.product_id === currentProductId)
    if (dupIdx !== -1) {
      const prodName = products.value.find(p => p.id === currentProductId)?.name || `ID=${currentProductId}`
      ElMessage.warning(`商品"${prodName}"已在第${dupIdx + 1}行，请直接修改数量`)
      form.value.items[idx].product_id = null
    }
  }
}

const showDialog = () => {
  form.value = { id: null, customer_name: '', project_id: null, deduct_inventory: false, tax_rate: 0.03, has_invoice: false, payment_status: 'unpaid', notes: '', image_url: '', total_price: null, items: [{ product_id: null, quantity: 1, unit_price: 0 }] }
  dialogVisible.value = true
  loadOptions()
}

const handleSave = async () => {
  const validItems = form.value.items.filter(i => i.product_id && i.quantity > 0)
  if (validItems.length === 0) { ElMessage.warning('请至少添加一个有效商品'); return }
  try {
    // 按名字查找已有客户，找不到则新建
    let customerId = null
    const customerName = (form.value.customer_name || '').trim()
    if (customerName) {
      const existing = customers.value.find(c => c.name === customerName)
      if (existing) {
        customerId = existing.id
      } else {
        const newCustomer = await api.createCustomer({ name: customerName })
        customerId = newCustomer.id
        customers.value.push(newCustomer)
      }
    }
    await api.createSale({
      customer_id: customerId,
      project_id: form.value.project_id,
      deduct_inventory: !form.value.project_id && !!form.value.deduct_inventory,
      has_invoice: form.value.has_invoice,
      payment_status: form.value.payment_status,
      notes: form.value.notes,
      total_price: form.value.total_price ?? undefined,
      items: validItems.map(i => ({ product_id: i.product_id, quantity: i.quantity, unit_price: i.unit_price }))
    })
    ElMessage.success('销售成功')
    dialogVisible.value = false
    loadData()
  } catch (e) { ElMessage.error('销售失败') }
}

const changeStatus = async (id, status) => {
  try {
    await api.updateSale(id, { status })
    ElMessage.success('状态已更新')
    loadData()
  } catch (e) { ElMessage.error('更新失败') }
}

const handleDelete = async (id) => {
  try {
    await api.deleteSale(id)
    ElMessage.success('已删除')
    loadData()
  } catch (e) { ElMessage.error('删除失败') }
}

const showEditDialog = (row) => {
  editForm.value = {
    id: row.id,
    customer_name: row.customer_name || '',
    project_id: row.project_id,
    deduct_inventory: row.deduct_inventory,
    has_invoice: row.has_invoice,
    payment_status: row.payment_status,
    notes: row.notes || '',
    image_url: row.image_url || '',
    total_price: row.total_price ?? null,
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
  // 销售单价由用户自行填写，不自动带商品指导价
  // ★ 防重：如果选的商品已存在于其他行，提示并清空
  const currentProductId = editForm.value.items[idx].product_id
  if (currentProductId) {
    const dupIdx = editForm.value.items.findIndex((item, i) => i !== idx && item.product_id === currentProductId)
    if (dupIdx !== -1) {
      const prodName = products.value.find(p => p.id === currentProductId)?.name || `ID=${currentProductId}`
      ElMessage.warning(`商品"${prodName}"已在第${dupIdx + 1}行，请直接修改数量`)
      editForm.value.items[idx].product_id = null
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
  try {
    // 按名字查找已有客户，找不到则新建
    let customerId = null
    const customerName = (editForm.value.customer_name || '').trim()
    if (customerName) {
      const existing = customers.value.find(c => c.name === customerName)
      if (existing) {
        customerId = existing.id
      } else {
        const newCustomer = await api.createCustomer({ name: customerName })
        customerId = newCustomer.id
        customers.value.push(newCustomer)
      }
    }
    await api.updateSale(editForm.value.id, {
      customer_id: customerId,
      project_id: editForm.value.project_id,
      deduct_inventory: !editForm.value.project_id && !!editForm.value.deduct_inventory,
      has_invoice: editForm.value.has_invoice,
      payment_status: editForm.value.payment_status,
      notes: editForm.value.notes,
      image_url: editForm.value.image_url,
      total_price: editForm.value.total_price ?? undefined,
      items: validItems.map(i => ({ product_id: i.product_id, quantity: i.quantity, unit_price: i.unit_price }))
    })
    if (validItems.length === 0) {
      ElMessage.success('销售单已删除（商品行数归零）')
    } else {
      ElMessage.success('销售单修改成功')
    }
    editDialogVisible.value = false
    loadData()
  } catch (e) { ElMessage.error('修改失败: ' + (e.response?.data?.detail || e.message)) }
}

const exportData = async (format) => {
  try {
    const params = {}
    if (dateRange.value) { params.start_date = dateRange.value[0]; params.end_date = dateRange.value[1] }
    await api.exportFile('sales', format, params)
  } catch (e) { ElMessage.error('导出失败') }
}

onMounted(loadData)
</script>