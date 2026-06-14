import { defineStore } from 'pinia'

export const useAccountStore = defineStore('account', {
  state: () => ({
    currentAccountId: localStorage.getItem('currentAccountId') || '',
    accounts: []
  }),

  getters: {
    currentAccount: (state) => {
      return state.accounts.find(a => String(a.id) === String(state.currentAccountId)) || { id: state.currentAccountId }
    }
  },

  actions: {
    setCurrentAccount(id) {
      this.currentAccountId = String(id)
      localStorage.setItem('currentAccountId', String(id))
    },
    setAccounts(list) {
      this.accounts = list
    }
  }
})