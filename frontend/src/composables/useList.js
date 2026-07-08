import { ref } from 'vue'
import { usePagination } from './usePagination'
import { handleError } from '../utils/errorHandler'

/**
 * 通用列表数据加载 composable
 *
 * 统一封装 list / loading / pagination / filters / reset / error 处理。
 * 适合非订单类简单列表页，复杂表单请用 useOrderList / useOrderPage。
 *
 * @param {Object} config
 * @param {Object} config.api - API 对象
 * @param {string} [config.method='getList'] - API 方法名
 * @param {Object} [config.staticParams={}] - 每次请求都带的固定参数
 * @param {Object} [config.defaultFilters={}] - 筛选默认值
 * @param {number} [config.defaultPageSize=20] - 默认页大小
 * @param {Function} [config.buildParams] - 将 filters 转成 API 参数，(filters) => params
 * @param {Function} [config.transform] - 解析响应，(res) => { items, total }
 * @param {Function} [config.onError] - 自定义错误处理
 */
export function useList(config) {
  const {
    api,
    method = 'getList',
    staticParams = {},
    defaultFilters = {},
    defaultPageSize = 20,
    buildParams = (filters) => filters,
    transform = (res) => ({ items: res.items || [], total: res.total || 0 }),
    onError
  } = config

  const list = ref([])
  const loading = ref(false)
  const filters = ref({ ...defaultFilters })

  const pagination = usePagination({
    defaultPageSize,
    onPageChange: loadData
  })

  async function loadData() {
    loading.value = true
    try {
      const requestParams = {
        page: pagination.page.value,
        page_size: pagination.pageSize.value,
        ...staticParams,
        ...buildParams(filters.value)
      }
      const res = await api[method](requestParams)
      const data = transform(res)
      list.value = data.items
      pagination.total.value = data.total
    } catch (e) {
      if (onError) {
        onError(e)
      } else {
        handleError(e, { defaultMsg: '加载失败' })
      }
    } finally {
      loading.value = false
    }
  }

  function search() {
    pagination.resetPage()
    loadData()
  }

  function reset() {
    filters.value = { ...defaultFilters }
    pagination.resetPage()
    loadData()
  }

  return {
    list,
    loading,
    filters,
    pagination,
    loadData,
    search,
    reset
  }
}
