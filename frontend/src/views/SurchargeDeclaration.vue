<template>
  <div>
    <AccountingTip page="surcharge" />
    <StatCards :items="[
      { label: '待申报期间', value: pendingCount, color: 'warning' },
      { label: '已申报', value: declaredCount, color: 'success' },
      { label: '全部期间', value: tableData.length, color: 'primary' }
    ]" />

    <el-card shadow="never">
      <template #header>
        <PageHeader title="附加税申报">
          <template #actions>
            <el-button size="small" type="primary" @click="refresh">刷新</el-button>
          </template>
        </PageHeader>
      </template>
      <el-table :data="tableData" stripe style="width:100%" v-loading="loading">
        <template #empty><el-empty description="暂无附加税申报数据" /></template>
        <el-table-column prop="period" label="所属期间" width="110" />
        <el-table-column label="日期范围" min-width="180">
          <template #default="{ row }">{{ row.period_range }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status_tag" size="small">{{ row.status_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="城建税" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.urban_construction_tax) }}</template>
        </el-table-column>
        <el-table-column label="教育费附加" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.education_surcharge) }}</template>
        </el-table-column>
        <el-table-column label="地方教育附加" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.local_education_surcharge) }}</template>
        </el-table-column>
        <el-table-column label="合计" width="120" align="right">
          <template #default="{ row }"><span style="font-weight:700;">{{ formatMoney(row.total) }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="center">
          <template #default="{ row }">
            <el-button v-if="row.status === 'surcharge_declared'" size="small" plain disabled>已申报</el-button>
            <el-button v-else size="small" type="primary" plain @click="openEdit(row)">录入附加税</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="录入附加税" width="540px" :close-on-click-modal="false">
      <el-form :model="editForm" label-width="0">
        <FormGroup title="附加税信息" color="primary">
          <FormField label="所属期间" label-width="100px"><el-input :model-value="editForm.period" disabled /></FormField>
          <FormField label="城建税" label-width="100px"><el-input-number v-model="editForm.urban_construction_tax" :precision="2" :min="0" :step="0.01" style="width:100%;" controls-position="right" /></FormField>
          <FormField label="教育费附加" label-width="100px"><el-input-number v-model="editForm.education_surcharge" :precision="2" :min="0" :step="0.01" style="width:100%;" controls-position="right" /></FormField>
          <FormField label="地方教育附加" label-width="100px"><el-input-number v-model="editForm.local_education_surcharge" :precision="2" :min="0" :step="0.01" style="width:100%;" controls-position="right" /></FormField>
          <FormField label="备注" label-width="100px"><el-input v-model="editForm.notes" type="textarea" :rows="2" /></FormField>
        </FormGroup>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">确认录入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { formatMoney } from '../utils/format'
import { handleError } from '../utils/errorHandler'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { getPendingDeclarations, getDeclarations, declareSurcharge } from '../api/taxDeclaration'
import AccountingTip from '../components/AccountingTip.vue'
import FormGroup from '../components/FormGroup.vue'
import FormField from '../components/FormField.vue'
import StatCards from '../components/StatCards.vue'
import PageHeader from '../components/PageHeader.vue'

const loading = ref(false)
const pending = ref([])
const declared = ref([])
const dialogVisible = ref(false)
const saving = ref(false)
const editForm = ref({
  period: '',
  urban_construction_tax: 0,
  education_surcharge: 0,
  local_education_surcharge: 0,
  notes: '',
})

const pendingCount = computed(() => pending.value.filter(p => !p.surcharge_declared).length)
const declaredCount = computed(() => pending.value.filter(p => p.surcharge_declared).length)

const tableData = computed(() => {
  const map = {}
  for (const d of declared.value) map[d.period] = d
  return pending.value.map(p => {
    const d = map[p.period]
    let status_tag = 'danger'
    let status_label = '待申报增值税'
    if (p.status === 'vat_declared') { status_label = '待录入附加税'; status_tag = 'warning' }
    else if (p.status === 'surcharge_declared') { status_label = '已申报'; status_tag = 'success' }
    else { status_label = '待申报增值税'; status_tag = 'danger' }
    return {
      period: p.period,
      period_range: `${(p.period_start || '').slice(0, 10)} ~ ${(p.period_end || '').slice(0, 10)}`,
      status: p.status, status_label, status_tag,
      urban_construction_tax: d ? (+(d.urban_construction_tax || d.surcharge_urban_construction_tax || 0)) : 0,
      education_surcharge: d ? (+(d.education_surcharge || d.surcharge_education_surcharge || 0)) : 0,
      local_education_surcharge: d ? (+(d.local_education_surcharge || d.surcharge_local_education_surcharge || 0)) : 0,
      total: d ? (+(d.total || d.surcharge_total || 0)) : 0,
    }
  })
})

const openEdit = (row) => {
  editForm.value = { period: row.period, urban_construction_tax: 0, education_surcharge: 0, local_education_surcharge: 0, notes: '' }
  dialogVisible.value = true
}

const handleSave = async () => {
  const f = editForm.value
  if (f.urban_construction_tax <= 0 && f.education_surcharge <= 0 && f.local_education_surcharge <= 0) {
    ElMessage.warning('至少有一项附加税金额大于 0')
    return
  }
  saving.value = true
  try {
    await declareSurcharge(f.period, {
      urban_construction_tax: f.urban_construction_tax,
      education_surcharge: f.education_surcharge,
      local_education_surcharge: f.local_education_surcharge,
      notes: f.notes,
    })
    ElMessage.success('附加税录入成功')
    dialogVisible.value = false
    await refresh()
  } catch (e) { handleError(e, { defaultMsg: '附加税录入失败' }) }
  finally { saving.value = false }
}

const fetchData = async () => {
  loading.value = true
  try {
    const [p, d] = await Promise.all([getPendingDeclarations(), getDeclarations()])
    pending.value = p || []
    declared.value = d || []
  } catch (e) { handleError(e, { defaultMsg: '加载附加税数据失败' }) }
  finally { loading.value = false }
}

const refresh = () => fetchData()

useAccountAwareData(fetchData)
</script>

<style scoped>
/* 样式已集中到 global.css */
</style>
