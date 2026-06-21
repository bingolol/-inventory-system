import { ref } from 'vue'

/**
 * 通用分页 composable
 *
 * 封装分页状态管理（页码、页大小、总数）。
 * 从 Sales.vue / Purchases.vue 提取，供所有分页场景复用。
 *
 * @param {Object} options
 * @param {number} [options.defaultPageSize=20] - 默认页大小
 * @param {Function} [options.onPageChange] - 翻页/切换页大小后的回调
 */
export function usePagination(options = {}) {
  const { defaultPageSize = 20, onPageChange } = options

  const page = ref(1)
  const pageSize = ref(defaultPageSize)
  const total = ref(0)

  const totalPages = () => Math.ceil(total.value / pageSize.value) || 1

  const onCurrentChange = () => {
    onPageChange?.()
  }

  const onSizeChange = () => {
    page.value = 1
    onPageChange?.()
  }

  const resetPage = () => {
    page.value = 1
  }

  const setTotal = (val) => {
    total.value = val
  }

  return {
    page,
    pageSize,
    total,
    totalPages,
    onCurrentChange,
    onSizeChange,
    resetPage,
    setTotal
  }
}