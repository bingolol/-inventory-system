import { defineStore } from 'pinia'

export const useAccountStore = defineStore('account', {
  state: () => ({
    currentAccountId: localStorage.getItem('currentAccountId') || '',
    accounts: []
  }),

  getters: {
    currentAccount: (state) => {
      return state.accounts.find(a => String(a.id) === state.currentAccountId) || { id: state.currentAccountId }
    }
  },

  actions: {
    setCurrentAccount(id) {
      const sid = String(id)
      this.currentAccountId = sid
      localStorage.setItem('currentAccountId', sid)
    },
    setAccounts(list) {
      this.accounts = list
    }
  }
})