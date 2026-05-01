import { reactive, readonly } from 'vue'

const state = reactive({
  currentAccountId: localStorage.getItem('currentAccountId') || '',
  accounts: []
})

export const accountStore = {
  get currentAccountId() { return state.currentAccountId },
  get accounts() { return state.accounts },
  get currentAccount() {
    return state.accounts.find(a => String(a.id) === String(state.currentAccountId)) || { id: state.currentAccountId }
  },
  setCurrentAccount(id) {
    state.currentAccountId = String(id)
    localStorage.setItem('currentAccountId', String(id))
  },
  setAccounts(list) {
    state.accounts = list
  }
}
