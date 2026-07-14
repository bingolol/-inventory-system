import { ref } from 'vue'
import { ElMessage } from 'element-plus'
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
    } catch (e) { ElMessage.warning('产品/伙伴列表加载失败，部分下拉选项不可用，请刷新重试') }
  }

  useAccountAwareData(loadData)
  enumsStore.fetchEnums()

  return {
    list, loading, keyword, dateRange, statusFilter, pagination,
    loadData, exportData, getSummaries,
    orderForm, enumsStore, products, partners, loadOptions
  }
}
