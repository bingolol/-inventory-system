<template>
  <div class="login-page">
    <el-card class="login-card">
      <template #header>
        <h2>进销存管理系统</h2>
      </template>
      <el-form @submit.prevent="handleLogin" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="username" placeholder="admin" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" placeholder="admin" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">
            登录
          </el-button>
        </el-form-item>
        <div v-if="error" style="color:red;text-align:center">{{ error }}</div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const username = ref('admin')
const password = ref('admin')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    await auth.login(username.value, password.value)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex; justify-content: center; align-items: center;
  height: 100vh; background: var(--bg-page);
}
.login-card {
  width: 400px;
  background: var(--bg-card) !important;
  border: 1px solid var(--border-lighter) !important;
}
.login-card h2 {
  color: var(--text-primary);
  font-family: var(--font-display);
}
</style>
