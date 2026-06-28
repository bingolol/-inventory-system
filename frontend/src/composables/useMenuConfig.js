export const companyMenuItems = [
  { index: '/', icon: 'DataAnalysis', label: '仪表盘' },
  {
    index: 'ops', icon: 'Sell', label: '业务处理',
    children: [
      { index: '/sales-customers', icon: 'Sell', label: '销售开单' },
      { index: '/supply-chain', icon: 'Box', label: '采购入库' },
      { index: '/invoices', icon: 'DocumentChecked', label: '发票录入' },
    ]
  },
  {
    index: 'finance', icon: 'Wallet', label: '财务核算',
    children: [
      { index: '/financial-overview', icon: 'DataBoard', label: '财务总览' },
      { index: '/bank-accounts', icon: 'Wallet', label: '银行账户' },
      { index: '/expenses', icon: 'Ticket', label: '费用管理' },
      { index: '/reconciliations', icon: 'Files', label: '对账管理' },
      { index: '/cash-flows', icon: 'TrendCharts', label: '现金流量表' },
    ]
  },
  {
    index: 'reports', icon: 'Document', label: '财务报表',
    children: [
      { index: '/financial-reports', icon: 'TrendCharts', label: '利润表/资产负债表' },
      { index: '/finance/journal/moves', icon: 'Document', label: '会计凭证' },
      { index: '/finance/reports/trial-balance', icon: 'DataLine', label: '试算平衡表' },
      { index: '/finance/receivable/aging', icon: 'Files', label: '往来账龄' },
      { index: '/tax-report', icon: 'DataBoard', label: '税务报表' },
    ]
  },
  {
    index: 'system', icon: 'Document', label: '系统管理',
    children: [
      { index: '/logs', icon: 'Document', label: '操作日志' },
      { index: '/backup', icon: 'FolderChecked', label: '数据备份' },
    ]
  },
]

export const personalMenuItems = [
  { index: '/personal', icon: 'Wallet', label: '流水账' },
  { index: '/logs', icon: 'Document', label: '操作日志' },
  { index: '/backup', icon: 'FolderChecked', label: '数据备份' },
]
