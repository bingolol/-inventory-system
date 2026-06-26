<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">往来账龄分析</span>
        </div>
      </template>

      <div class="filter-bar">
        <el-radio-group v-model="partnerType" @change="onPartnerTypeChange">
          <el-radio value="customer">客户</el-radio>
          <el-radio value="supplier">供应商</el-radio>
        </el-radio-group>
        <el-select v-model="partnerId" placeholder="选择往来单位" filterable :disabled="!partners.length" style="width: 240px;">
          <el-option v-for="p in partners" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-date-picker v-model="asOfDate" type="date" placeholder="截止日期" value-format="YYYY-MM-DD" />
        <el-button type="primary" @click="loadData" :disabled="!partnerId">查询</el-button>
      </div>

      <div v-loading="loading">
        <template v-if="result">
          <el-card shadow="never" class="balance-card">
            <div class="balance-row">
              <span class="balance-label">{{ partnerType === 'customer' ? '客户' : '供应商' }}应收/应付余额</span>
              <span class="balance-value">¥{{ formatMoney(result.balance) }}</span>
            </div>
          </el-card>

          <el-table :data="agingRows" stripe border style="margin-top: 16px;">
            <template #empty><el-empty description="暂无账龄数据" /></template>
            <el-table-column prop="bucket" label="账龄区间" width="160" />
            <el-table-column label="金额" align="right" min-width="200">
              <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
            </el-table-column>
          </el-table>
        </template>
        <el-empty v-else-if="!loading" description="请选择往来单位后查询" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import dayjs from 'dayjs'
import { getPartnerReceivable } from '../api/finance'
import { getCustomers, getSuppliers } from '../api/partners'
import { formatMoney } from '../utils/format'
import { handleError } from '../api/index'
import { useAccountAwareData } from '../composables/useAccountAwareData'

const loading = ref(false)
const partnerType = ref('customer')
const partners = ref([])
const partnerId = ref(null)
const asOfDate = ref(dayjs().format('YYYY-MM-DD'))
const result = ref(null)

const agingRows = computed(() => {
  if (!result.value || !result.value.aging) return []
  return Object.entries(result.value.aging).map(([bucket, amount]) => ({
    bucket: AGING_BUCKET_LABELS[bucket] || bucket,
    amount: Number(amount),
  }))
})

const AGING_BUCKET_LABELS = {
  '0-30': '未逾期（0-30天）',
  '31-60': '31-60天',
  '61-90': '61-90天',
  '90+': '90天以上',
}

const loadPartners = async () => {
  partnerId.value = null
  result.value = null
  try {
    const api = partnerType.value === 'customer' ? getCustomers : getSuppliers
    const res = await api({ page_size: 1000 })
    partners.value = res.items || []
  } catch (e) {
    handleError(e, { defaultMsg: '加载往来单位列表失败' })
  }
}

const onPartnerTypeChange = () => {
  loadPartners()
}

const loadData = async () => {
  if (!partnerId.value) return
  loading.value = true
  try {
    const res = await getPartnerReceivable(partnerId.value, {
      partner_type: partnerType.value,
      as_of_date: asOfDate.value,
    })
    result.value = res
  } catch (e) {
    handleError(e, { defaultMsg: '加载账龄分析失败' })
  } finally {
    loading.value = false
  }
}

useAccountAwareData(() => {
  loadPartners()
})
</script>

<style scoped>
.balance-card {
  margin-bottom: 0;
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-7);
}
.balance-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.balance-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}
.balance-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--el-color-primary);
}
</style>
