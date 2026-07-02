import { defineStore } from 'pinia'
import api from '../api/index'

const STORAGE_KEY_TOKEN = 'auth_access_token'
const STORAGE_KEY_REFRESH = 'auth_refresh_token'
const STORAGE_KEY_USERNAME = 'auth_username'
const STORAGE_KEY_ACCOUNT_ID = 'auth_account_id'
const STORAGE_KEY_EXPIRES = 'auth_expires_at'

function _now() {
  return Date.now()
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: localStorage.getItem(STORAGE_KEY_TOKEN) || '',
    refreshToken: localStorage.getItem(STORAGE_KEY_REFRESH) || '',
    username: localStorage.getItem(STORAGE_KEY_USERNAME) || '',
    accountId: parseInt(localStorage.getItem(STORAGE_KEY_ACCOUNT_ID) || '0'),
    expiresAt: parseInt(localStorage.getItem(STORAGE_KEY_EXPIRES) || '0'),
  }),

  getters: {
    isLoggedIn: (state) => !!state.accessToken && _now() < state.expiresAt,
    needsRefresh: (state) => !!state.refreshToken && !!state.accessToken && _now() >= state.expiresAt - 300000,
  },

  actions: {
    _persist() {
      if (this.accessToken) {
        localStorage.setItem(STORAGE_KEY_TOKEN, this.accessToken)
        localStorage.setItem(STORAGE_KEY_REFRESH, this.refreshToken)
        localStorage.setItem(STORAGE_KEY_USERNAME, this.username)
        localStorage.setItem(STORAGE_KEY_ACCOUNT_ID, String(this.accountId))
        localStorage.setItem(STORAGE_KEY_EXPIRES, String(this.expiresAt))
      }
    },

    _clearStorage() {
      localStorage.removeItem(STORAGE_KEY_TOKEN)
      localStorage.removeItem(STORAGE_KEY_REFRESH)
      localStorage.removeItem(STORAGE_KEY_USERNAME)
      localStorage.removeItem(STORAGE_KEY_ACCOUNT_ID)
      localStorage.removeItem(STORAGE_KEY_EXPIRES)
    },

    async login(username, password) {
      const data = await api.post('/auth/login', { username, password })
      this.accessToken = data.access_token
      this.refreshToken = data.refresh_token
      this.username = data.username
      this.accountId = data.account_id
      this.expiresAt = _now() + (data.expires_in || 7200) * 1000
      this._persist()
      return data
    },

    async register(username, password) {
      const data = await api.post('/auth/register', { username, password })
      this.accessToken = data.access_token
      this.refreshToken = data.refresh_token
      this.username = data.username
      this.accountId = data.account_id
      this.expiresAt = _now() + (data.expires_in || 7200) * 1000
      this._persist()
      return data
    },

    async refresh() {
      if (!this.refreshToken) return false
      try {
        const data = await api.post('/auth/refresh', { refresh_token: this.refreshToken })
        this.accessToken = data.access_token
        this.expiresAt = _now() + (data.expires_in || 7200) * 1000
        this._persist()
        return true
      } catch {
        this.logout()
        return false
      }
    },

    async checkSession() {
      if (!this.accessToken) return false
      if (this.needsRefresh) {
        return await this.refresh()
      }
      if (!this.isLoggedIn) return false
      try {
        await api.get('/auth/me')
        return true
      } catch {
        return false
      }
    },

    async logout() {
      try {
        await api.post('/auth/logout')
      } catch {
        // ignore logout errors
      }
      this.accessToken = ''
      this.refreshToken = ''
      this.username = ''
      this.accountId = 0
      this.expiresAt = 0
      this._clearStorage()
    },
  },
})
