import { ref } from 'vue'
import financeApi from '../api/finance'
import ordersApi from '../api/orders'
import productsApi from '../api/products'
import expensesApi from '../api/expenses'
import invoicesApi from '../api/invoices'
import { getMonthRange, currentQuarter } from '../utils/date'

export function useDashboardData() {
  const loading = ref(false)
  const profitLoss = ref({ total_revenue: 0, total_cost: 0, gross_profit: 0, total_expenses: 0, net_profit: 0, sale_count: 0 })
  const inventory = ref({ total_stock_value: 0, total_quantity: 0, product_count: 0, low_stock_count: 0, negative_stock_count: 0 })
  const receivable = ref({ total_receivable: 0, unpaid_customer_count: 0, total_payable: 0, unpaid_supplier_count: 0 })
  const tax = ref({ vat_payable: 0, income_tax_payable: 0, total_tax: 0, period_label: '' })
  const trendData = ref([])
  const alerts = ref([])
  const trendDays = ref(7)

  async function loadProfit() {
    const range = getMonthRange()
    const [profitRes, expRes] = await Promise.all([
      financeApi.getProfitReport({ start_date: range.start, end_date: range.end }).catch(() => null),
      expensesApi.getExpenses({ year: range.year, limit: 99999 }).catch(() => null)
    ])
    const rev = Number(profitRes?.total_revenue ?? 0)
    const cost = Number(profitRes?.total_cost ?? 0)
    const totalExpenses = Array.isArray(expRes?.items)
      ? expRes.items
          .filter(e => {
            const d = new Date(e.expense_date)
            return d.getMonth() + 1 === range.month && d.getFullYear() === range.year
          })
          .reduce((s, e) => s + Number(e.amount || 0), 0)
      : 0
    profitLoss.value = {
      total_revenue: rev,
      total_cost: cost,
      gross_profit: rev - cost,
      total_expenses: totalExpenses,
      net_profit: rev - cost - totalExpenses,
      sale_count: profitRes?.sale_count ?? 0
    }
  }

  async function loadInventory() {
    const [overview, alertList] = await Promise.all([
      financeApi.getOverview().catch(() => null),
      productsApi.getAlerts().catch(() => [])
    ])
    alerts.value = Array.isArray(alertList) ? alertList : []
    inventory.value = {
      total_stock_value: Number(overview?.total_stock_value ?? 0),
      total_quantity: Number(overview?.total_inventory_quantity ?? 0),
      product_count: Number(overview?.total_products ?? 0),
      low_stock_count: alerts.value.length,
      negative_stock_count: Number(overview?.negative_stock_count ?? 0)
    }
  }

  async function loadReceivable() {
    const [salesRes, purchRes] = await Promise.all([
      ordersApi.getSales({ page: 1, page_size: 1000 }).catch(() => null),
      ordersApi.getPurchases({ page: 1, page_size: 1000 }).catch(() => null)
    ])
    const saleItems = Array.isArray(salesRes?.items) ? salesRes.items : []
    const purchItems = Array.isArray(purchRes?.items) ? purchRes.items : []
    const unpaidSales = saleItems.filter(o => o.payment_status === 'unpaid')
    const unpaidPurchases = purchItems.filter(o => o.payment_status === 'unpaid')
    const customerNames = new Set(unpaidSales.map(o => o.customer_name).filter(Boolean))
    const supplierNames = new Set(unpaidPurchases.map(o => o.supplier_name).filter(Boolean))
    receivable.value = {
      total_receivable: unpaidSales.reduce((s, o) => s + Number(o.total_price || 0), 0),
      unpaid_customer_count: customerNames.size,
      total_payable: unpaidPurchases.reduce((s, o) => s + Number(o.total_price || 0), 0),
      unpaid_supplier_count: supplierNames.size
    }
  }

  async function loadTax() {
    const range = getMonthRange()
    const year = range.year
    const month = range.month
    const quarter = currentQuarter()
    const [vatRes, incomeRes] = await Promise.all([
      invoicesApi.getTaxReportMonthly(year, month).catch(() => null),
      invoicesApi.getIncomeTaxReport(year, quarter).catch(() => null)
    ])
    const vat = Number(vatRes?.tax_payable ?? 0)
    const incomeTax = Number(incomeRes?.tax_amount ?? 0)
    tax.value = {
      vat_payable: vat,
      income_tax_payable: incomeTax,
      total_tax: vat + incomeTax,
      period_label: `${year}年${quarter}季度`
    }
  }

  async function loadTrend(days) {
    const d = days ?? trendDays.value
    try {
      trendData.value = await financeApi.getTrend({ days: d })
    } catch (e) {
      trendData.value = []
    }
  }

  async function loadAll() {
    if (loading.value) return
    loading.value = true
    await Promise.all([
      loadProfit(),
      loadInventory(),
      loadReceivable(),
      loadTax(),
      loadTrend()
    ])
    loading.value = false
  }

  function reload() {
    return loadAll()
  }

  return {
    loading,
    profitLoss,
    inventory,
    receivable,
    tax,
    alerts,
    trendData,
    trendDays,
    loadAll,
    loadTrend,
    reload
  }
}
