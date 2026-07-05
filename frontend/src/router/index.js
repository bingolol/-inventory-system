import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { title: '登录' } },
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '仪表盘', desc: '快速导航到各功能模块' } },
  // ── 基础数据 ──
  { path: '/partners', name: 'PartnerManagement', component: () => import('../views/PartnerManagement.vue'), meta: { title: '伙伴管理', desc: '客户 · 供应商' } },
  { path: '/suppliers', redirect: '/partners?tab=suppliers' },
  { path: '/customers', redirect: '/partners' },
  { path: '/inventory-goods', name: 'InventoryGoods', component: () => import('../views/InventoryGoods.vue'), meta: { title: '库存商品', desc: '商品目录 · 库存明细' } },
  { path: '/products', redirect: '/inventory-goods' },
  { path: '/inventory', redirect: '/inventory-goods?tab=inventory' },
  // ── 业务处理 ──
  { path: '/sales-customers', name: 'SalesCustomers', component: () => import('../views/SalesCustomers.vue'), meta: { title: '销售管理', desc: '创建和管理销售订单' } },
  { path: '/supply-chain', name: 'SupplyChain', component: () => import('../views/SupplyChain.vue'), meta: { title: '供应链管理', desc: '采购 · 库存 · 供应商 · 商品' } },
  { path: '/invoices', name: 'Invoices', component: () => import('../views/Invoices.vue'), meta: { title: '发票管理', desc: '销项/进项发票录入和查询' } },
  { path: '/funds/transactions', name: 'FundTransactions', component: () => import('../views/FundTransactions.vue'), meta: { title: '资金流水', desc: '收款 · 付款统一管理' } },
  { path: '/receipts', redirect: '/funds/transactions' },
  { path: '/payments', redirect: '/funds/transactions' },
  // ── 资金账户 ──
  { path: '/bank-accounts', name: 'BankAccounts', component: () => import('../views/BankAccounts.vue'), meta: { title: '银行账户', desc: '管理各银行账户余额及流水，由业务自动生成' } },
  { path: '/bank-reconcile', name: 'BankReconcile', component: () => import('../views/BankReconcile.vue'), meta: { title: '银行对账', desc: '银行对账单导入、对账、调节表确认' } },
  // ── 费用资产 ──
  { path: '/expense-outlay', name: 'ExpenseOutlay', component: () => import('../views/ExpenseOutlay.vue'), meta: { title: '费用支出', desc: '费用管理 · 个人垫付' } },
  { path: '/expenses', redirect: '/expense-outlay' },
  { path: '/personal-advances', redirect: '/expense-outlay?tab=advances' },
  { path: '/fixed-assets', name: 'FixedAssets', component: () => import('../views/FixedAssets.vue'), meta: { title: '固定资产', desc: '资产台账 · 折旧 · 处置' } },
  // ── 报表分析 ──
  { path: '/financial-reports', name: 'FinancialReports', component: () => import('../views/FinancialReports.vue'), meta: { title: '财务报表', desc: '资产负债表 · 利润表 · 期初余额' } },
  { path: '/financial-overview', name: 'FinancialOverview', component: () => import('../views/FinancialOverview.vue'), meta: { title: '财务总览', desc: '关键财务指标概览' } },
  { path: '/cash-flows', name: 'CashFlows', component: () => import('../views/CashFlow.vue'), meta: { title: '现金流量表', desc: '经营活动 · 投资活动 · 筹资活动现金流' } },
  { path: '/finance/books', name: 'AccountingBooks', component: () => import('../views/AccountingBooks.vue'), meta: { title: '会计账簿', desc: '凭证查询 · 试算平衡表' } },
  { path: '/accounting-guide', name: 'AccountingGuide', component: () => import('../views/AccountingGuide.vue'), meta: { title: '会计规则指引', desc: '零基础 · 用实际数据讲会计' } },
  { path: '/finance/journal/moves', redirect: '/finance/books' },
  { path: '/finance/reports/trial-balance', redirect: '/finance/books?tab=trial' },
  { path: '/finance/receivable/aging', name: 'AgingReport', component: () => import('../views/AgingReport.vue'), meta: { title: '往来管理', desc: '对账汇总 · 账龄分析' } },
  { path: '/reconciliations', redirect: '/finance/receivable/aging' },
  { path: '/period-end-tax', name: 'PeriodEndTax', component: () => import('../views/PeriodEndTax.vue'), meta: { title: '期末税务', desc: '税务报表 · 期末处理' } },
  { path: '/tax-report', redirect: '/period-end-tax' },
  { path: '/period-close', redirect: '/period-end-tax?tab=close' },
  // ── 系统管理 ──
  { path: '/logs', name: 'Logs', component: () => import('../views/Logs.vue'), meta: { title: '操作日志', desc: '查看系统所有操作记录' } },
  { path: '/backup', name: 'Backup', component: () => import('../views/Backup.vue'), meta: { title: '数据备份', desc: '备份和恢复系统数据' } },
  // ── 个人账本 ──
  { path: '/personal', name: 'Personal', component: () => import('../views/Personal.vue'), meta: { title: '个人流水', desc: '个人账本收支记录' } },
  // ── 404 ──
  { path: '/:pathMatch(.*)*', name: 'NotFound', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  document.title = `${to.meta.title || '进销存'} - 进销存管理系统`
  if (to.name !== 'Login') {
    const auth = useAuthStore()
    if (!auth.isLoggedIn) {
      // 先尝试 refresh，失败则自动登录（无密码）
      const refreshed = auth.refreshToken ? await auth.refresh() : false
      if (!refreshed) {
        try {
          await auth.autoLogin()
        } catch {
          return '/login'
        }
      }
    }
  }
})

export default router
