import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '仪表盘' } },
  { path: '/products', name: 'Products', component: () => import('../views/Products.vue'), meta: { title: '商品管理' } },
  { path: '/suppliers', name: 'Suppliers', component: () => import('../views/Suppliers.vue'), meta: { title: '供应商管理' } },
  { path: '/customers', name: 'Customers', component: () => import('../views/Customers.vue'), meta: { title: '客户管理' } },
  { path: '/purchases', name: 'Purchases', component: () => import('../views/Purchases.vue'), meta: { title: '采购管理' } },
  { path: '/sales', name: 'Sales', component: () => import('../views/Sales.vue'), meta: { title: '销售管理' } },
  { path: '/inventory', name: 'Inventory', component: () => import('../views/Inventory.vue'), meta: { title: '库存管理' } },
  { path: '/reports', name: 'Reports', component: () => import('../views/Reports.vue'), meta: { title: '报表统计' } },
  { path: '/invoices', name: 'Invoices', component: () => import('../views/Invoices.vue'), meta: { title: '发票管理' } },
  { path: '/tax-report', name: 'TaxReport', component: () => import('../views/TaxReport.vue'), meta: { title: '税务报表' } },
  { path: '/cash-flows', name: 'CashFlow', component: () => import('../views/CashFlow.vue'), meta: { title: '现金流量表' } },
  { path: '/financial-reports', name: 'FinancialReports', component: () => import('../views/FinancialReports.vue'), meta: { title: '财务报表' } },
  { path: '/expenses', name: 'Expenses', component: () => import('../views/Expenses.vue'), meta: { title: '费用管理' } },
  { path: '/logs', name: 'Logs', component: () => import('../views/Logs.vue'), meta: { title: '操作日志' } },
  { path: '/personal', name: 'Personal', component: () => import('../views/Personal.vue'), meta: { title: '个人流水账' } },
  { path: '/backup', name: 'Backup', component: () => import('../views/Backup.vue'), meta: { title: '数据备份' } },
  { path: '/reconciliations', name: 'Reconciliations', component: () => import('../views/Reconciliations.vue'), meta: { title: '对账管理' } },
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
})

export default router