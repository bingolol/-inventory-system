export const companyMenuItems = [
  { index: '/', icon: 'DataAnalysis', label: '仪表盘' },
  {
    index: 'master', icon: 'Files', label: '基础数据',
    children: [
      { index: '/partners', icon: 'User', label: '伙伴管理' },
      { index: '/inventory-goods', icon: 'Box', label: '库存商品' },
    ]
  },
  {
    index: 'ops', icon: 'Sell', label: '业务处理',
    children: [
      { index: '/sales-customers', icon: 'Sell', label: '销售开单' },
      { index: '/supply-chain', icon: 'Box', label: '采购入库' },
      { index: '/invoices', icon: 'DocumentChecked', label: '发票录入' },
      { index: '/funds/transactions', icon: 'Money', label: '资金流水' },
    ]
  },
  {
    index: 'finance', icon: 'Wallet', label: '财务核算',
    children: [
      { index: '/financial-overview', icon: 'DataBoard', label: '财务总览' },
      { index: '/expense-outlay', icon: 'Ticket', label: '费用管理' },
      { index: '/fixed-assets', icon: 'OfficeBuilding', label: '固定资产' },
      { index: '/bank-accounts', icon: 'Wallet', label: '银行账户' },
      { index: '/bank-reconcile', icon: 'Files', label: '银行对账' },
      { index: '/finance/receivable/aging', icon: 'Connection', label: '往来管理' },
    ]
  },
  {
    index: 'reports', icon: 'Document', label: '财务报表',
    children: [
      { index: '/financial-reports', icon: 'TrendCharts', label: '资产负债表/利润表' },
      { index: '/cash-flows', icon: 'TrendCharts', label: '现金流量表' },
      { index: '/finance/books', icon: 'Document', label: '会计账簿' },
      { index: '/accounting-guide', icon: 'Document', label: '会计规则指引' },
    ]
  },
  {
    index: 'period', icon: 'Calendar', label: '期末处理',
    children: [
      { index: '/period-end-tax', icon: 'DataBoard', label: '期末税务' },
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
