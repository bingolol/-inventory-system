import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { title: '登录' } },
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '仪表盘', desc: '快速导航到各功能模块' } },
  { path: '/products', name: 'Products', component: () => import('../views/Products.vue'), meta: { title: '商品管理' } },
  { path: '/suppliers', name: 'Suppliers', component: () => import('../views/Suppliers.vue'), meta: { title: '供应商管理' } },
  { path: '/customers', name: 'Customers', component: () => import('../views/Customers.vue'), meta: { title: '客户管理' } },
  { path: '/purchases', name: 'Purchases', component: () => import('../views/Purchases.vue'), meta: { title: '采购管理' } },
  { path: '/sales', name: 'Sales', component: () => import('../views/Sales.vue'), meta: { title: '销售管理' } },
  { path: '/sales-customers', name: 'SalesCustomers', component: () => import('../views/SalesCustomers.vue'), meta: { title: '销售管理', desc: '创建和管理销售订单' } },
  { path: '/supply-chain', name: 'SupplyChain', component: () => import('../views/SupplyChain.vue'), meta: { title: '供应链管理', desc: '采购 · 库存 · 供应商 · 商品' } },
  { path: '/inventory', name: 'Inventory', component: () => import('../views/Inventory.vue'), meta: { title: '库存管理' } },
  { path: '/reports', name: 'Reports', component: () => import('../views/Reports.vue'), meta: { title: '报表统计' } },
  { path: '/invoices', name: 'Invoices', component: () => import('../views/Invoices.vue'), meta: { title: '发票管理', desc: '销项/进项发票录入和查询' } },
  { path: '/tax-report', name: 'TaxReport', component: () => import('../views/TaxReport.vue'), meta: { title: '税务报表', desc: '增值税 · 企业所得税计算和申报' } },
  { path: '/cash-flows', name: 'CashFlow', component: () => import('../views/CashFlow.vue'), meta: { title: '现金流量表', desc: '查看按经营/投资/筹资分类的现金流' } },
  { path: '/financial-reports', name: 'FinancialReports', component: () => import('../views/FinancialReports.vue'), meta: { title: '财务报表', desc: '资产负债表 · 利润表 · 期初余额' } },
  { path: '/financial-overview', name: 'FinancialOverview', component: () => import('../views/FinancialOverview.vue'), meta: { title: '财务总览', desc: '资产负债、利润、现金流、费用一站式查看' } },
  { path: '/bank-accounts', name: 'BankAccounts', component: () => import('../views/BankAccounts.vue'), meta: { title: '银行账户', desc: '管理各银行账户余额及流水，由业务自动生成' } },
  { path: '/expenses', name: 'Expenses', component: () => import('../views/Expenses.vue'), meta: { title: '费用管理', desc: '录入和管理日常经营费用' } },
  { path: '/logs', name: 'Logs', component: () => import('../views/Logs.vue'), meta: { title: '操作日志', desc: '查看系统所有操作记录' } },
  { path: '/backup', name: 'Backup', component: () => import('../views/Backup.vue'), meta: { title: '数据备份', desc: '备份和恢复系统数据' } },
  { path: '/reconciliations', name: 'Reconciliations', component: () => import('../views/Reconciliations.vue'), meta: { title: '对账管理', desc: '供应商/客户往来账款核对' } },
  { path: '/finance/reports/trial-balance', name: 'TrialBalance', component: () => import('../views/TrialBalance.vue'), meta: { title: '试算平衡表' } },
  { path: '/finance/journal/moves', name: 'JournalMoves', component: () => import('../views/JournalMoves.vue'), meta: { title: '凭证查询' } },
  { path: '/finance/receivable/aging', name: 'AgingReport', component: () => import('../views/AgingReport.vue'), meta: { title: '往来账龄' } },
  { path: '/:pathMatch(.*)*', name: 'NotFound', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  document.title = `${to.meta.title || '进销存'} - 进销存管理系统`
  if (to.name !== 'Login') {
    const auth = useAuthStore()
    if (!auth.isLoggedIn) {
      return '/login'
    }
  }
})

export default router