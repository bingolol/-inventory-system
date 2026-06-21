import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import accountsApi from '../api/accounts'
import { handleError } from '../api/index'

/**
 * 账本管理 composable
 *
 * 封装账本的重建、重命名、删除逻辑，从 Layout.vue 提取。
 *
 * @param {Object} config
 * @param {Ref} config.accounts - 账本列表 ref
 * @param {Object} config.accountStore - useAccountStore() 实例
 * @param {Function} config.onAccountsChanged - 账本列表变更后的回调（如重新加载）
 */
export function useAccountManagement({ accounts, accountStore, onAccountsChanged }) {
  // ── 重命名 ──
  const renameDialogVisible = ref(false)
  const renameForm = ref({ name: '' })
  const renameLoading = ref(false)

  const openRenameDialog = () => {
    const acc = accounts.value.find(a => a.id === Number(accountStore.currentAccountId))
    if (!acc) { ElMessage.warning('请先选择一个账本'); return }
    renameForm.value.name = acc.name
    renameDialogVisible.value = true
  }

  const handleRename = async () => {
    const name = renameForm.value.name.trim()
    if (!name) { ElMessage.warning('账本名称不能为空'); return }
    renameLoading.value = true
    try {
      await accountsApi.updateAccount(Number(accountStore.currentAccountId), { name })
      ElMessage.success('账本名称已更新')
      renameDialogVisible.value = false
      await onAccountsChanged()
    } catch (e) {
      handleError(e, { defaultMsg: '修改失败' })
    } finally {
      renameLoading.value = false
    }
  }

  // ── 新建 ──
  const createDialogVisible = ref(false)
  const createForm = ref({ name: '', type: 'company', taxpayer_type: 'small_scale' })
  const createLoading = ref(false)

  const openCreateDialog = () => {
    createForm.value = { name: '', type: 'company', taxpayer_type: 'small_scale' }
    createDialogVisible.value = true
  }

  const handleCreate = async () => {
    const name = createForm.value.name.trim()
    if (!name) { ElMessage.warning('账本名称不能为空'); return }
    createLoading.value = true
    try {
      const newAccount = await accountsApi.createAccount({
        name,
        type: createForm.value.type,
        taxpayer_type: createForm.value.taxpayer_type
      })
      ElMessage.success('账本已创建')
      createDialogVisible.value = false
      await onAccountsChanged()
      accountStore.setCurrentAccount(newAccount.id)
    } catch (e) {
      handleError(e, { defaultMsg: '创建失败' })
    } finally {
      createLoading.value = false
    }
  }

  // ── 删除 ──
  const openDeleteConfirm = () => {
    const acc = accounts.value.find(a => a.id === Number(accountStore.currentAccountId))
    if (!acc) { ElMessage.warning('请先选择一个账本'); return }
    ElMessageBox.confirm(
      `确定要删除账本「${acc.name}」吗？该操作不可撤销，删除前请确保账本下无业务数据。`,
      '删除账本',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
      }
    ).then(async () => {
      try {
        await accountsApi.deleteAccount(acc.id)
        ElMessage.success('账本已删除')
        await onAccountsChanged()
        if (accounts.value.length > 0) {
          accountStore.setCurrentAccount(accounts.value[0].id)
        } else {
          accountStore.setCurrentAccount('')
        }
      } catch (e) {
        handleError(e, { defaultMsg: '删除失败' })
      }
    }).catch(() => {})
  }

  return {
    renameDialogVisible, renameForm, renameLoading, openRenameDialog, handleRename,
    createDialogVisible, createForm, createLoading, openCreateDialog, handleCreate,
    openDeleteConfirm
  }
}
