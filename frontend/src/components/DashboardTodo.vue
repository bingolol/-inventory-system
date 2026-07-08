<template>
  <div class="d-todo-box">
    <div class="d-todo-hd">
      <span class="d-todo-title">待办清单</span>
      <span class="d-todo-date">{{ currentDateLabel }} · {{ periodLabel }}</span>
    </div>
    <div class="d-todo-body">
      <template v-for="(group, gi) in taskGroups" :key="gi">
        <div class="d-todo-section" v-if="group.items.length">
          <div class="d-todo-section-hd" :class="group.cls">{{ group.label }}</div>
          <div v-for="(item, ii) in group.items" :key="ii" class="d-todo-item" :class="{ 'is-urgent': item.urgent }">
            <div class="d-todo-info">
              <div class="d-todo-label">{{ item.label }}</div>
              <div class="d-todo-desc">{{ item.desc }}</div>
              <div class="d-todo-deadline" v-if="item.deadline">截止：{{ item.deadline }}</div>
            </div>
            <el-button v-if="item.route" size="small" :type="item.urgent ? 'danger' : 'default'" plain @click="$router.push(item.route)">{{ item.action }}</el-button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getPendingDeclarations } from '../api/taxDeclaration'
import { today, currentQuarter } from '../utils/date'
const [year, month, day] = today().split('-').map(Number)
const quarter = currentQuarter(); const weekday = new Date().getDay()

const qs = (quarter - 1) * 3 + 1
const currentDateLabel = computed(() => `${year}年${month}月${day}日`)
const periodLabel = computed(() => `${year}年第${quarter}季度（${qs}月~${qs + 2}月）`)

const isMonthEnd = day >= 25
const isQuarterEnd = month % 3 === 0
const isQuarterEndClose = isQuarterEnd && isMonthEnd
const isQuarterStart15 = month % 3 === 1 && day <= 15
const isMonthStart = day <= 7
const isMon = weekday === 1 || weekday === 0
const isJan = month === 1
const isBetweenJanMay = (month < 5) || (month === 5 && day <= 31)
const isJulToSep = month >= 7 && month <= 9
const isDec = month === 12
const is15th = day <= 15
const next15th = quarter < 4 ? `${quarter * 3}月15日` : `${year + 1}年1月15日`

const pendingDeclarations = ref([])

onMounted(async () => {
  try {
    const r = await getPendingDeclarations()
    pendingDeclarations.value = r || []
  } catch (e) {
    // 静默失败，不阻塞页面
  }
})

const surchargePending = computed(() =>
  pendingDeclarations.value.filter(p => p.status === 'vat_declared' && !p.surcharge_declared)
)

const taskGroups = computed(() => [
  { label: '本月截止', cls: 'd-todo-sh-urgent', items: buildUrgent() },
  { label: '本月例行', cls: 'd-todo-sh-monthly', items: buildMonthly() },
  { label: '日常维护', cls: 'd-todo-sh-routine', items: buildRoutine() },
  { label: '远期注意', cls: 'd-todo-sh-future', items: buildFuture() },
])

function buildUrgent() {
  const t = []
  if (isQuarterEndClose) t.push({ label: `${year}年第${quarter}季度末 — 必须执行月结`, desc: '季度末月结：系统自动完成计提折旧、计算增值税、计提附加税、计提企业所得税。不做月结报表就是空的，也不知道该缴多少所得税。', deadline: `${month}月最后一天`, urgent: true, route: '/period-end-tax?tab=close', action: '执行月结' })
  else if (isMonthEnd) t.push({ label: `${month}月末 — 准备月结`, desc: '确保本月所有采购、销售、费用已录入，发票已登记，银行流水已核对。数据不齐月结出来的报表就不准。', deadline: `${month}月最后一天`, urgent: true, route: '/period-end-tax?tab=close', action: '准备月结' })
  if (isMonthStart && !isQuarterEndClose) t.push({ label: `${month}月初 — 检查上月月结`, desc: '上月还没做月结的话尽快补做。月结不仅生成报表，还计提折旧、计算增值税，不做数据会跨月混淆。', deadline: `${month}月7日前`, urgent: false, route: '/period-end-tax?tab=close', action: '补做月结' })
  if (isQuarterStart15 && !isJan) t.push({ label: `上季度申报截止 — 增值税+企业所得税预缴`, desc: `必须在${next15th}前完成。逾期每日万分之五滞纳金！`, deadline: next15th, urgent: true, route: '/period-end-tax', action: '查税务报表' })
  if (isBetweenJanMay) t.push({ label: `企业所得税年度汇算清缴（${year}年5月31日截止）`, desc: `完成${year - 1}年度企业所得税年度申报。${month >= 5 ? '本月最后期限，切勿逾期！' : '尽早准备，别拖到最后。'}`, deadline: '5月31日', urgent: month >= 4, route: '/period-end-tax', action: '查所得税' })
  if (isBetweenJanMay || (month === 6 && day <= 30)) t.push({ label: `工商年报（${year}年6月30日截止）`, desc: `国家企业信用信息公示系统报送上年度工商年报。不报将被列入经营异常名录，影响贷款和招投标。${month >= 6 ? '本月最后期限！' : ''}`, deadline: '6月30日', urgent: month >= 6 })

  for (const p of surchargePending.value) {
    const daysOverdue = day > 15 ? day - 15 : 0
    let label, desc, urgent, deadline
    if (daysOverdue > 0) {
      label = `⚠️ ${p.period} 附加税未录入（已逾期${daysOverdue}天）`
      desc = `VAT 已申报，附加税尚未录入。逾期申报可能产生滞纳金。建议立即补录。`
      urgent = true
      deadline = `逾期${daysOverdue}天`
    } else if (day <= 6) {
      label = `📌 ${p.period} 附加税待录入`
      desc = `VAT 已申报，请在本月15号前录入附加税。需要根据税务局核定的金额填写。`
      urgent = false
      deadline = `本月15日前`
    } else {
      label = `🔔 ${p.period} 附加税待录入（即将截止）`
      desc = `VAT 已申报，距截止日期仅剩${15 - day}天。`
      urgent = day > 10
      deadline = `本月15日前`
    }
    t.push({ label, desc, urgent, deadline, route: '/period-end-tax?tab=surcharge', action: '录入附加税' })
  }

  return t
}

function buildMonthly() {
  const t = []
  if (is15th) t.push({ label: `${month}月15日前 — 完成上月税务申报`, desc: '一般纳税人必须每月15日前申报增值税。小规模按季度申报，但仍建议每月查看税务掌握税负。', route: '/period-end-tax', action: '查税务' })
  t.push({ label: `${month}月工资计提与发放`, desc: '有员工的公司每月需记录工资费用：费用支出 → 新增费用 → 类别选"工资"。', route: '/expense-outlay', action: '记费用' })
  if (isMonthEnd) t.push({ label: `${month}月末 — 存货盘点核对`, desc: '系统库存数 vs 实际仓库数。有差异及时做盘点调整（需填写原因）。库存不准，成本利润全错。', route: '/inventory-goods?tab=inventory', action: '盘库存' })
  if (day >= 20) t.push({ label: '检查发票余量', desc: '月底前确认剩余发票数量够用。快用完的话赶紧去税务局申领。', route: '/invoices', action: '看发票' })
  return t
}

function buildRoutine() {
  const t = []
  t.push({ label: isMon ? '本周核对银行流水' : '核对银行对账单（建议每周一次）', desc: '确保系统账面余额和银行实际余额一致。差异可能来自银行手续费未录、客户汇款未核销、支票未兑现。', route: '/bank-reconcile', action: '去对账' })
  t.push({ label: '催收逾期应收账款', desc: '重点关注超过90天未回款的客户。金额大的主动联系催收，逾期越久变坏账概率越大。', route: '/finance/receivable/aging', action: '查往来' })
  t.push({ label: '当天业务当天录入系统', desc: '采购入库、销售开单、费用支出、收款付款——每笔发生立刻录入，不要积压。' })
  return t
}

function buildFuture() {
  const t = []
  if (isJulToSep) t.push({ label: '残疾人就业保障金申报（7-9月）', desc: '各地申报时间略有不同。未安置残疾人需缴纳残保金，具体金额和截止时间咨询当地残联。', deadline: '以当地通知为准' })
  t.push({ label: '关注连续12个月累计销售额', desc: '小规模纳税人连续12个月销售额超500万会被强制认定一般纳税人（不可逆）。每月要盯着滚动12个月的累计数。', deadline: '持续关注' })
  if (!isDec && month >= 10) t.push({ label: `${year}年度即将结束 — 提前准备年结`, desc: `还有${12 - month}个月年底。年前需：清理暂估入库、核对应收应付、盘点固定资产、确认全年费用完整。提前准备比年底突击效率高得多。`, deadline: '12月31日' })
  if (isDec) t.push({ label: '会计档案年度归档', desc: '年底后整理全年档案：凭证、账簿、报表、发票存根、银行对账单等。纸质档案保存30年，电子档案永久保存。', deadline: `${year + 1}年3月31日` })
  return t
}
</script>

<style scoped>
.d-todo-box { background: var(--bg-card); border: 1px solid var(--border-lighter); border-radius: 12px; overflow: hidden; }
.d-todo-hd { display: flex; justify-content: space-between; align-items: baseline; padding: 14px 18px; border-bottom: 1px solid var(--border-lighter); }
.d-todo-title { font-size: 13px; font-weight: 700; color: var(--text-primary); }
.d-todo-date { font-size: 11px; color: var(--text-placeholder); }
.d-todo-body { padding: 0; }
.d-todo-section { border-bottom: 1px solid var(--border-lighter); }
.d-todo-section:last-child { border-bottom: none; }
.d-todo-section-hd { padding: 8px 18px 4px; font-size: 11px; font-weight: 600; letter-spacing: 0.3px; }
.d-todo-sh-urgent { color: var(--danger); }
.d-todo-sh-monthly { color: var(--warning); }
.d-todo-sh-routine { color: var(--success); }
.d-todo-sh-future { color: var(--text-placeholder); }
.d-todo-item { display: flex; gap: 12px; align-items: flex-start; padding: 10px 18px; transition: background .15s; }
.d-todo-item + .d-todo-item { border-top: 1px solid var(--border-lighter); }
.d-todo-item:hover { background: var(--bg-hover); }
.d-todo-item.is-urgent { background: var(--danger-light); }
.d-todo-item.is-urgent:hover { background: #fde8e8; }
.d-todo-info { flex: 1; min-width: 0; }
.d-todo-label { font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px; }
.d-todo-desc { font-size: 12px; color: var(--text-secondary); line-height: 1.6; }
.d-todo-deadline { font-size: 11px; color: var(--danger); margin-top: 4px; font-weight: 500; }
</style>
