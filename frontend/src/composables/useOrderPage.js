import { ref } from 'vue'
import productsApi from '../api/products'
import { useOrderList } from './useOrderList'
import { useOrderForm } from './useOrderForm'
import { useAccountAwareData } from './useAccountAwareData'
import { useEnumsStore } from '../stores/enums'

export function useOrderPage(config) {
  const { orderType, api, exportType, autoFillPrice } = config

  const enumsStore = useEnumsStore()

  const orderList = useOrderList({ api: { getList: api.getList }, exportType })
  const { list, loading, keyword, dateRange, statusFilter, pagination, loadData, exportData, getSummaries } = orderList

  const orderForm = useOrderForm({ orderType, api, onSuccess: loadData, autoFillPrice })

  const products = ref([])
  const partners = ref([])

  async function loadOptions(getPartnersFn) {
    try {
      const [pRes, partRes] = await Promise.all([
        productsApi.getProducts({ page: 1, page_size: 1000 }),
        getPartnersFn({ page: 1, page_size: 1000 })
      ])
      products.value = pRes.items || pRes
      partners.value = partRes.items || partRes
    } catch (e) { /* options loading errors are non-critical */ }
  }

  useAccountAwareData(loadData)
  enumsStore.fetchEnums()

  return {
    list, loading, keyword, dateRange, statusFilter, pagination,
    loadData, exportData, getSummaries,
    orderForm, enumsStore, products, partners, loadOptions
  }
}
