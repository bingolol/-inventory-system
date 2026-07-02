<template>
  <div class="tax-template-preview">
    <div class="tt-sheet-title">{{ sheetTitle }}</div>
    <div class="tt-sheet-subtitle">适用执行小企业会计准则的企业</div>
    <div class="tt-form-code">{{ formCode }}&nbsp;&nbsp;&nbsp;&nbsp;单位：元</div>

    <div class="tt-form-info">
      <div class="tt-info-row">
        <span class="tt-info-label">纳税人识别号</span>
        <span class="tt-info-value">{{ data?.taxpayer_id || '-' }}</span>
        <span class="tt-info-label">纳税人名称</span>
        <span class="tt-info-value">{{ data?.taxpayer_name || '-' }}</span>
      </div>
      <div class="tt-info-row">
        <span class="tt-info-label">所属期起</span>
        <span class="tt-info-value">{{ data?.period_start || '-' }}</span>
        <span class="tt-info-label">所属期止</span>
        <span class="tt-info-value">{{ data?.period_end || '-' }}</span>
      </div>
    </div>

    <!-- 资产负债表：左右双栏 -->
    <template v-if="sheet === 'bs'">
      <table class="tt-table tt-bs">
        <thead>
          <tr>
            <th class="tt-col-item">资产</th>
            <th class="tt-col-line">行次</th>
            <th class="tt-col-amt">期末余额</th>
            <th class="tt-col-amt">年初余额</th>
            <th class="tt-col-item">负债和所有者权益</th>
            <th class="tt-col-line">行次</th>
            <th class="tt-col-amt">期末余额</th>
            <th class="tt-col-amt">年初余额</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in bsRows" :key="idx" :class="rowClass(row.left, row.right)">
            <td :class="['tt-left', indentClass(row.left.name)]">{{ row.left.name }}</td>
            <td class="tt-center">{{ row.left.lineNo }}</td>
            <td class="tt-right">{{ fmt(row.left.endAmt) }}</td>
            <td class="tt-right">{{ fmt(row.left.startAmt) }}</td>
            <td :class="['tt-left', indentClass(row.right.name)]">{{ row.right.name }}</td>
            <td class="tt-center">{{ row.right.lineNo }}</td>
            <td class="tt-right">{{ fmt(row.right.endAmt) }}</td>
            <td class="tt-right">{{ fmt(row.right.startAmt) }}</td>
          </tr>
        </tbody>
      </table>
    </template>

    <!-- 利润表 / 现金流量表：单栏 -->
    <template v-else>
      <table class="tt-table tt-single">
        <thead>
          <tr>
            <th class="tt-col-item">项目</th>
            <th class="tt-col-line">行次</th>
            <th class="tt-col-amt">本期金额</th>
            <th class="tt-col-amt">本年累计金额</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.line_no" :class="singleRowClass(item)">
            <td :class="['tt-left', indentClass(item.name)]">{{ item.name }}</td>
            <td class="tt-center">{{ item.line_no }}</td>
            <td class="tt-right">{{ fmt(item.period_amount) }}</td>
            <td class="tt-right">{{ fmt(item.cumulative_amount) }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatMoney } from '../utils/format'

const props = defineProps({
  data: { type: Object, default: () => ({}) },
  sheet: { type: String, default: 'bs' }, // bs | is | cf
})

const sheetTitle = computed(() => {
  return { bs: '资产负债表', is: '利润表', cf: '现金流量表' }[props.sheet]
})

const formCode = computed(() => {
  return { bs: '会小企01表', is: '会小企02表', cf: '会小企03表' }[props.sheet]
})

const items = computed(() => {
  if (props.sheet === 'bs') return props.data?.balance_sheet || []
  if (props.sheet === 'is') return props.data?.income_statement || []
  return props.data?.cash_flow_statement || []
})

const bsRows = computed(() => {
  const arr = items.value
  const left = arr.filter(i => i.line_no <= 30)
  const right = arr.filter(i => i.line_no > 30)
  const max = Math.max(left.length, right.length)
  const rows = []
  for (let i = 0; i < max; i++) {
    rows.push({
      left: wrap(left[i]),
      right: wrap(right[i]),
    })
  }
  return rows
})

function wrap(item) {
  if (!item) return { name: '', lineNo: '', endAmt: '', startAmt: '', periodAmt: '', cumulativeAmt: '' }
  return {
    name: item.name || '',
    lineNo: item.line_no ?? '',
    endAmt: item.end_amount,
    startAmt: item.start_amount,
    periodAmt: item.period_amount,
    cumulativeAmt: item.cumulative_amount,
  }
}

function fmt(v) {
  if (v === '' || v === null || v === undefined) return ''
  const n = Number(v)
  if (Number.isNaN(n)) return v
  return formatMoney(n)
}

function indentClass(name) {
  if (!name) return ''
  if (name.startsWith('  ') || name.startsWith('其中') || name.startsWith('减：')) return 'tt-indent-2'
  if (name.startsWith('        ') || name.startsWith('       ')) return 'tt-indent-3'
  return ''
}

function isSection(name) {
  return name && (name.includes('：') || name.includes('一、') || name.includes('二、') || name.includes('三、')) && !name.includes('其中')
}

function isTotal(name) {
  return name && (name.includes('合计') || name.includes('总计') || name.includes('净额'))
}

function rowClass(left, right) {
  const l = left?.name || ''
  const r = right?.name || ''
  if (isSection(l) || isSection(r)) return 'tt-section'
  if (isTotal(l) || isTotal(r)) return 'tt-total'
  return ''
}

function singleRowClass(item) {
  const n = item?.name || ''
  if (isSection(n)) return 'tt-section'
  if (isTotal(n)) return 'tt-total'
  return ''
}
</script>

<style scoped>
.tax-template-preview {
  background: #fff;
  color: #000;
  font-family: 'SimSun', '宋体', serif;
  font-size: 13px;
  padding: 16px;
  border: 1px solid #ccc;
}

.tt-sheet-title {
  text-align: center;
  font-size: 20px;
  font-weight: bold;
  margin-bottom: 4px;
}

.tt-sheet-subtitle {
  text-align: center;
  font-size: 12px;
  margin-bottom: 4px;
}

.tt-form-code {
  text-align: right;
  font-size: 12px;
  margin-bottom: 12px;
}

.tt-form-info {
  margin-bottom: 12px;
}

.tt-info-row {
  display: flex;
  gap: 24px;
  margin-bottom: 6px;
}

.tt-info-label {
  font-weight: bold;
  min-width: 90px;
}

.tt-info-value {
  min-width: 180px;
  border-bottom: 1px solid #000;
  padding: 0 8px;
}

.tt-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.tt-table th,
.tt-table td {
  border: 1px solid #000;
  padding: 4px 6px;
  vertical-align: middle;
}

.tt-table thead th {
  background: #f5f5f5;
  font-weight: bold;
  text-align: center;
}

.tt-bs .tt-col-item { width: 22%; }
.tt-bs .tt-col-line { width: 8%; }
.tt-bs .tt-col-amt { width: 12%; }

.tt-single .tt-col-item { width: 55%; }
.tt-single .tt-col-line { width: 10%; }
.tt-single .tt-col-amt { width: 17.5%; }

.tt-left { text-align: left; }
.tt-center { text-align: center; }
.tt-right { text-align: right; font-family: 'Courier New', monospace; }

.tt-section {
  font-weight: bold;
}

.tt-total {
  font-weight: bold;
}

.tt-indent-2 {
  padding-left: 24px !important;
}

.tt-indent-3 {
  padding-left: 48px !important;
}
</style>
