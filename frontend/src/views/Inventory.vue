<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <PageHeader title="库存管理">
          <template #actions>
            <el-dropdown>
              <el-button><el-icon><Download /></el-icon> 导出</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="exportData('excel')">Excel</el-dropdown-item>
                  <el-dropdown-item @click="exportData('csv')">CSV</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </PageHeader>
      </template>
      <FilterBar @search="loadData" @reset="resetFilters">
        <el-input v-model="filters.search" placeholder="搜索商品名称/编码" clearable style="width:220px" @clear="loadData" @keyup.enter="loadData">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filters.category" placeholder="分类筛选" clearable style="width:140px" @change="loadData">
          <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
        </el-select>
        <el-switch v-model="filters.alert_only" active-text="仅显示预警" @change="loadData" />
      </FilterBar>
      <el-table :data="list" v-loading="loading" stripe style="width:100%">
        <el-table-column prop="product_sku" label="编码" min-width="110" />
        <el-table-column prop="product_name" label="商品名称" min-width="140" />
        <el-table-column prop="product_category" label="分类" min-width="100" />
        <el-table-column prop="product_unit" label="单位" min-width="70" />
        <el-table-column label="当前库存" min-width="100">
          <template #default="{ row }">
            <span :class="{ 'negative-stock': row.quantity < 0, 'alert-stock': row.quantity >= 0 && row.is_alert }">
              {{ row.quantity }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="min_stock" label="预警线" min-width="80" />
        <el-table-column label="预警" min-width="70">
          <template #default="{ row }">
            <StatusTag v-if="row.quantity < 0" status="negative" color="danger" label="负库存" />
            <StatusTag v-else-if="row.is_alert" status="alert" color="warning" label="不足" />
            <StatusTag v-else status="normal" color="success" label="正常" />
          </template>
        </el-table-column>
        <el-table-column prop="purchase_price" label="进价" min-width="110" align="right">
          <template #default="{ row }"><span class="money">¥{{ formatMoney(row.purchase_price) }}</span></template>
        </el-table-column>
        <el-table-column prop="sale_price" label="售价" min-width="110" align="right">
          <template #default="{ row }"><span class="money">¥{{ formatMoney(row.sale_price) }}</span></template>
        </el-table-column>
        <el-table-column label="库存价值" min-width="120" align="right">
          <template #default="{ row }"><span class="money">¥{{ formatMoney(row.total_value ?? 0) }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <ActionColumn :actions="[{ key: 'adjust', label: '盘点' }]" @click="(key) => { if (key === 'adjust') showAdjust(row) }" />
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="pagination.page.value" v-model:page-size="pagination.pageSize.value" :total="pagination.total.value" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next" @current-change="loadData" @size-change="pagination.onSizeChange" />
      </div>
    </el-card>

    <el-dialog v-model="adjustVisible" title="库存盘点调整" width="450px" destroy-on-close>
      <el-form :model="adjustForm" label-width="80px">
        <el-form-item label="商品">
          <span style="font-weight:600;">{{ adjustForm.product_name }}</span>
        </el-form-item>
        <el-form-item label="当前库存">
          <span :class="{ 'negative-stock': adjustForm.current_quantity < 0 }">{{ adjustForm.current_quantity }}</span>
        </el-form-item>
        <el-form-item label="新库存量" required>
          <el-input-number v-model="adjustForm.quantity" style="width:100%" />
        </el-form-item>
        <el-form-item label="调整原因" required>
          <el-input v-model="adjustForm.reason" type="textarea" :rows="2" placeholder="请填写调整原因，如：盘盈、盘亏、损坏、过期、丢失、纠错等" />
        </el-form-item>
        <el-alert v-if="adjustForm.quantity < 0" title="注意：将产生负库存" type="warning" :closable="false" show-icon style="margin-top:8px" />
      </el-form>
      <template #footer>
        <el-button @click="adjustVisible = false">取消</el-button>
        <el-popconfirm
          :title="`确认将库存从 ${adjustForm.current_quantity} 调整为 ${adjustForm.quantity}？`"
          confirm-button-text="确认"
          cancel-button-text="取消"
          @confirm="handleAdjust"
        >
          <template #reference>
            <el-button type="primary" :disabled="!adjustForm.reason || adjustForm.quantity === adjustForm.current_quantity">确认调整</el-button>
          </template>
        </el-popconfirm>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Search } from '@element-plus/icons-vue'
import productsApi from '../api/products'
import exportApi from '../api/export'
import { formatMoney } from '../utils/format'
import { handleError } from '../api/index'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { useList } from '../composables/useList'
import PageHeader from '../components/PageHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import FilterBar from '../components/FilterBar.vue'
import ActionColumn from '../components/ActionColumn.vue'

const { list, loading, filters, pagination, loadData, reset } = useList({
  api: productsApi,
  method: 'getInventory',
  defaultFilters: { search: '', category: '', alert_only: false },
  buildParams: (f) => {
    const params = { alert_only: f.alert_only }
    if (f.search) params.search = f.search
    if (f.category) params.category = f.category
    return params
  },
  onError: (e) => handleError(e, { defaultMsg: '加载库存数据失败，请检查网络连接' })
})

const resetFilters = () => reset()

const categories = ref([])
const adjustVisible = ref(false)
const adjustForm = ref({ product_id: null, product_name: '', current_quantity: 0, quantity: 0, reason: '' })

const showAdjust = (row) => {
  adjustForm.value = {
    product_id: row.product_id,
    product_name: row.product_name,
    current_quantity: Number(row.quantity) || 0,
    quantity: Number(row.quantity) || 0,
    reason: ''
  }
  adjustVisible.value = true
}

const handleAdjust = async () => {
  try {
    await productsApi.adjustInventory(adjustForm.value.product_id, { quantity: adjustForm.value.quantity, reason: adjustForm.value.reason })
    ElMessage.success('库存已调整')
    adjustVisible.value = false
    loadData()
  } catch (e) { handleError(e, { defaultMsg: '调整失败，请检查输入数量是否正确' }) }
}

const loadCategories = async () => {
  try { categories.value = await productsApi.getCategories() } catch (e) { console.error('[Inventory] 加载分类失败', e) }
}

const exportData = async (format) => {
  try {
    const params = { alert_only: filters.value.alert_only }
    if (filters.value.search) params.search = filters.value.search
    if (filters.value.category) params.category = filters.value.category
    await exportApi.exportFile('inventory', format, params)
  } catch (e) { handleError(e, { defaultMsg: '导出失败，请检查文件权限和磁盘空间' }) }
}

useAccountAwareData(loadData)
loadCategories()
</script>

<style scoped></style>
