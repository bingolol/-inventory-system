import { ref } from 'vue'
import { usePagination } from './usePagination'
import commonApi from '../api/common'
import { handleError } from '../api/index'

/**
 * 订单列表 composable
 * 
 * 封装采购/销售列表的加载、筛选、导出等通用逻辑
 * 
 * @param {Object} config
 * @param {Object} config.api - API对象，需包含 getList 方法
 * @param {string} config.exportType - 导出类型 ('purchases' | 'sales')
 * @param {Object} [config.defaultFilters={}] - 默认筛选条件
 */
export function useOrderList(config) {
  const { api, exportType, defaultFilters = {} } = config
  
  const list = ref([])
  const loading = ref(false)
  const keyword = ref('')
  const dateRange = ref(null)
  const statusFilter = ref('')
  
  const pagination = usePagination({ 
    defaultPageSize: 20, 
    onPageChange: loadData 
  })
  
  async function loadData() {
    loading.value = true
    try {
      const params = {
        page: pagination.page.value,
        page_size: pagination.pageSize.value,
        ...defaultFilters
      }
      if (keyword.value) params.keyword = keyword.value
      if (dateRange.value) {
        params.start_date = dateRange.value[0]
        params.end_date = dateRange.value[1]
      }
      if (statusFilter.value) params.status = statusFilter.value

      const res = await api.getList(params)
      pagination.total.value = res.total
      list.value = res.items
    } catch (e) {
      handleError(e, { defaultMsg: '加载失败' })
    } finally {
      loading.value = false
    }
  }
  
  async function exportData(format) {
    try {
      const params = { ...defaultFilters }
      if (keyword.value) params.keyword = keyword.value
      if (dateRange.value) { 
        params.start_date = dateRange.value[0]
        params.end_date = dateRange.value[1] 
      }
      if (statusFilter.value) params.status = statusFilter.value
      await commonApi.exportFile(exportType, format, params)
    } catch (e) { 
      handleError(e, { defaultMsg: '导出失败' })
    }
  }
  
  function resetFilters() {
    keyword.value = ''
    dateRange.value = null
    statusFilter.value = ''
    loadData()
  }
  
  return {
    list,
    loading,
    keyword,
    dateRange,
    statusFilter,
    pagination,
    loadData,
    exportData,
    resetFilters
  }
}
