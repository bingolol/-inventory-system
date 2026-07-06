<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <span class="page-title">操作日志</span>
      </template>
      <div class="filter-bar">
        <el-select v-model="entityType" placeholder="实体类型" clearable style="width:140px" @change="loadData">
          <el-option label="商品" value="product" />
          <el-option label="供应商" value="supplier" />
          <el-option label="客户" value="customer" />
          <el-option label="采购单" value="purchase_order" />
          <el-option label="销售单" value="sale_order" />
          <el-option label="库存" value="inventory" />
        </el-select>
        <el-select v-model="operation" placeholder="操作类型" clearable style="width:120px" @change="loadData">
          <el-option label="创建" value="create" />
          <el-option label="更新" value="update" />
          <el-option label="删除" value="delete" />
          <el-option label="盘点" value="adjust" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="loadData" />
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>
      <el-table :data="list" stripe style="width:100%" v-loading="loading">
        <template #empty>
          <el-empty description="暂无操作日志" />
        </template>
        <el-table-column prop="created_at" label="时间" min-width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="operation" label="操作" min-width="100">
          <template #default="{ row }">
            <el-tag :type="opTagType(row.operation)" size="small">{{ opLabel(row.operation) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="entity_type" label="类型" min-width="100">
          <template #default="{ row }">{{ entityLabel(row.entity_type) }}</template>
        </el-table-column>
        <el-table-column prop="entity_id" label="ID" min-width="80" />
        <el-table-column prop="operator" label="操作者" min-width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.operator === 'ai' ? 'warning' : 'primary'" size="small">
              {{ row.operator === 'ai' ? 'AI' : '我' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" min-width="200" />
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[20,50,100]" layout="total, sizes, prev, pager, next" @current-change="loadData" @size-change="loadData" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import commonApi from '../api/common'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { formatDateTime } from '../utils/format'
import { handleError } from '../api/index'

const list = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const entityType = ref('')
const operation = ref('')
const dateRange = ref(null)

const opLabel = (op) => ({ create: '创建', update: '更新', delete: '删除', adjust: '盘点' }[op] || op)
const opTagType = (op) => ({ create: 'success', update: 'warning', delete: 'danger', adjust: 'info' }[op] || '')
const entityLabel = (type) => ({ product: '商品', supplier: '供应商', customer: '客户', purchase_order: '采购单', sale_order: '销售单', inventory: '库存', expense: '费用', invoice: '发票', personal: '个人流水' }[type] || type)

const loadData = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (entityType.value) params.entity_type = entityType.value
    if (operation.value) params.operation = operation.value
    if (dateRange.value) { params.start_date = dateRange.value[0]; params.end_date = dateRange.value[1] }
    const res = await commonApi.getLogs(params)
    total.value = res.total
    list.value = res.items
  } catch (e) { handleError(e, { defaultMsg: '加载操作日志失败，请检查网络连接' }) }
  finally { loading.value = false }
}

useAccountAwareData(loadData)
</script>

<style scoped></style>