import { defineStore } from 'pinia'
import api from '../api/index'
import { API_BASE_URL } from '../api/index'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('auth_token') || '',
    username: localStorage.getItem('auth_username') || '',
    accountId: parseInt(localStorage.getItem('auth_account_id') || '0'),
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
  },
  actions: {
    async login(username, password) {
      const data = await api.post('/auth/login', { username, password })
      this.token = data.token
      this.username = data.username
      this.accountId = data.account_id
      localStorage.setItem('auth_token', this.token)
      localStorage.setItem('auth_username', this.username)
      localStorage.setItem('auth_account_id', String(this.accountId))
      return data
    },
    logout() {
      this.token = ''
      this.username = ''
      this.accountId = 0
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_username')
      localStorage.removeItem('auth_account_id')
    },
  },
})
