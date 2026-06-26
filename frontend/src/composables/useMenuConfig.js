/**
 * 侧边栏菜单配置
 *
 * 从 Layout.vue 提取，数据驱动渲染。
 * icon 字段为 Element Plus 图标组件名，模板中通过 <component :is> 动态渲染。
 */

export const companyMenuItems = [
  { index: '/', icon: 'DataAnalysis', label: '仪表盘' },
  { index: '/products', icon: 'Goods', label: '商品管理' },
  { index: '/suppliers', icon: 'OfficeBuilding', label: '供应商管理' },
  { index: '/customers', icon: 'User', label: '客户管理' },
  { index: '/purchases', icon: 'ShoppingCart', label: '采购管理' },
  { index: '/sales', icon: 'Sell', label: '销售管理' },
  { index: '/inventory', icon: 'Box', label: '库存管理', badge: 'alertCount' },
  {
    index: 'finance', icon: 'Document', label: '财务方向',
    children: [
      { index: '/financial-reports', icon: 'TrendCharts', label: '财务报表' },
      { index: '/cash-flows', icon: 'Wallet', label: '现金流量表' },
      { index: '/expenses', icon: 'Ticket', label: '费用管理' },
    ]
  },
  {
    index: 'tax', icon: 'DataLine', label: '税务方向',
    children: [
      { index: '/tax-report', icon: 'DataBoard', label: '税务报表' },
      { index: '/invoices', icon: 'DocumentChecked', label: '发票管理' },
    ]
  },
  { index: '/reconciliations', icon: 'Files', label: '对账管理' },
  { index: '/logs', icon: 'Document', label: '操作日志' },
  { index: '/backup', icon: 'FolderChecked', label: '数据备份' },
]

export const personalMenuItems = [
  { index: '/personal', icon: 'Wallet', label: '流水账' },
  { index: '/logs', icon: 'Document', label: '操作日志' },
  { index: '/backup', icon: 'FolderChecked', label: '数据备份' },
]
