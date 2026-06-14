import { watch, getCurrentScope, onScopeDispose } from 'vue'
import { useAccountStore } from '../stores/account'

/**
 * 账本切换时自动刷新数据
 * 
 * 监听 accountStore.currentAccountId 变化，自动调用传入的数据加载函数。
 * 使用 immediate: true，因此也替代了 onMounted 的初始加载职责。
 * 组件卸载时自动停止 watcher，防止对已卸载组件触发响应式更新。
 * 
 * @param {...Function} loadFns 数据加载函数，账本切换时依次调用
 */
export function useAccountAwareData(...loadFns) {
  const accountStore = useAccountStore()

  const stop = watch(
    () => accountStore.currentAccountId,
    () => { loadFns.forEach(fn => fn()) },
    { immediate: true }
  )

  if (getCurrentScope()) {
    onScopeDispose(stop)
  }
}