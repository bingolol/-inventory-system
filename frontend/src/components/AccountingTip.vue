<template>
  <div v-if="visible" class="acctip">
    <span class="acctip-icon">?</span>
    <div class="acctip-body">
      <div class="acctip-text">{{ currentTip.text }}</div>
      <a class="acctip-link" href="/accounting-guide" @click.prevent="$router.push('/accounting-guide')">{{ currentTip.linkText || '查看完整会计规则指引 →' }}</a>
    </div>
    <span class="acctip-close" @click="dismiss" title="关闭提示">✕</span>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({ page: { type: String, required: true } })
const visible = ref(true)

const tips = {
  'tax': {
    text: '增值税是你替税务局代收的钱（销项-进项），不是你自己的费用。企业所得税才是你赚了钱要缴的税（利润×税率）。两条线完全不同，别搞混。',
    linkText: '查看增值税和企业所得税详解 →'
  },
  'financial': {
    text: '资产负债表看家底（某一天你有多少资产、欠多少债），利润表看成绩（一段时期赚了还是亏了），现金流量表看钱包（真金白银进出）。三张表互相勾稽，一张出错另两张必然不平。',
    linkText: '查看三大报表详解 →'
  },
  'cashflow': {
    text: '利润表说赚了100万，银行账户可能只多了30万——剩下的全是赊账。现金流量表告诉你手里到底有多少现金。经营现金流为正，公司才算真正在造血。',
    linkText: '查看现金流量表详解 →'
  },
  'invoices': {
    text: '销项发票（你开给客户的）产生销项税，进项发票（供应商开给你的）可用于抵扣。小规模纳税人普票季度≤30万免税，专票始终按1%缴税。一般纳税人则需要认证后才能抵扣进项。',
    linkText: '查看增值税详解 →'
  },
  'expenses': {
    text: '费用分五大类：管理费用（房租水电工资）、销售费用（广告运输）、财务费用（银行手续费）、税金及附加（城建税等）、所得税费用。增值税不属于费用！',
    linkText: '查看费用分类详解 →'
  },
  'assets': {
    text: '买设备/电脑/车不能一次性记费用，要按使用年限分期折旧。每月折旧会减少利润，月末结账时系统会自动计提。原值 − 累计折旧 = 净值，这就是你家当现在还值多少钱。',
    linkText: '查看月结和折旧详解 →'
  },
  'aging': {
    text: '应收账款是你卖货没收到的钱（客户欠你的），应付账款是你进货没付的钱（你欠供应商的）。往来账龄告诉你每笔欠款欠了多久，超过90天要重点催收，超过一年可能变坏账。',
    linkText: '查看往来管理详解 →'
  },
  'surcharge': {
    text: '附加税（城建税、教育费附加、地方教育附加）是以你实际缴纳的增值税为基数计算的。系统不再自动推算——你需要根据税务局核定的金额手动录入，录入即自动过账生成凭证。',
    linkText: '查看附加税申报详解 →'
  }
}

const currentTip = computed(() => tips[props.page] || { text: '', linkText: '' })
const storageKey = computed(() => `tip-dismissed-${props.page}`)

const dismiss = () => { visible.value = false; try { localStorage.setItem(storageKey.value, '1') } catch {} }

onMounted(() => { try { if (localStorage.getItem(storageKey.value) === '1') visible.value = false } catch {} })
</script>

<style scoped>
.acctip {
  display: flex; gap: 12px; align-items: flex-start;
  padding: 12px 16px; border-radius: 8px;
  border-left: 4px solid var(--primary);
  background: var(--primary-light);
  margin-bottom: 16px; position: relative;
}
.acctip-icon { font-size: 16px; flex-shrink: 0; margin-top: 1px; }
.acctip-body { flex: 1; min-width: 0; }
.acctip-text { font-size: 13px; color: var(--text-regular); line-height: 1.7; }
.acctip-link { display: inline-block; margin-top: 6px; font-size: 12px; color: var(--primary); text-decoration: none; font-weight: 600; }
.acctip-link:hover { text-decoration: underline; }
.acctip-close { flex-shrink: 0; font-size: 13px; color: var(--text-placeholder); cursor: pointer; padding: 2px 4px; border-radius: 4px; line-height: 1; }
.acctip-close:hover { color: var(--danger); background: var(--bg-hover); }
</style>
