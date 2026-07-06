<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-brand">
        <div class="brand-icon">
          <svg viewBox="0 0 48 48" width="48" height="48">
            <rect x="6" y="20" width="10" height="20" rx="2" fill="currentColor" opacity="0.7"/>
            <rect x="19" y="12" width="10" height="28" rx="2" fill="currentColor" opacity="0.85"/>
            <rect x="32" y="6" width="10" height="34" rx="2" fill="currentColor"/>
          </svg>
        </div>
        <h1 class="brand-title">进销存管理系统</h1>
        <p class="brand-desc">库存 · 采购 · 销售 · 财务 一体化管理</p>
      </div>

      <el-card class="login-card" shadow="never">
        <template v-if="!isReady">
          <div class="loading-state">
            <el-icon class="is-loading" :size="24"><Loading /></el-icon>
            <span>正在检查系统状态...</span>
          </div>
        </template>

        <template v-else-if="isFirstTime">
          <div class="setup-header">
            <el-icon :size="28" color="#409EFF"><CircleCheckFilled /></el-icon>
            <div>
              <h3 class="setup-title">欢迎使用</h3>
              <p class="setup-desc">首次使用，请创建管理员账号</p>
            </div>
          </div>

          <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="handleRegister">
            <el-form-item prop="username">
              <el-input
                v-model="form.username"
                placeholder="用户名"
                size="large"
                :prefix-icon="UserIcon"
              />
            </el-form-item>

            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="密码"
                size="large"
                :prefix-icon="LockIcon"
                show-password
              />
            </el-form-item>

            <el-form-item prop="confirmPassword">
              <el-input
                v-model="form.confirmPassword"
                type="password"
                placeholder="确认密码"
                size="large"
                :prefix-icon="LockIcon"
                show-password
                @keyup.enter="handleRegister"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                native-type="submit"
                :loading="loading"
                size="large"
                class="login-btn"
              >
                {{ loading ? '初始化中...' : '初始化系统' }}
              </el-button>
            </el-form-item>
          </el-form>
        </template>

        <template v-else>
          <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="handleLogin">
            <el-form-item prop="username">
              <el-input
                v-model="form.username"
                placeholder="用户名"
                size="large"
                :prefix-icon="UserIcon"
                @keyup.enter="handleLogin"
              />
            </el-form-item>

            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="密码"
                size="large"
                :prefix-icon="LockIcon"
                show-password
                @keyup.enter="handleLogin"
              />
            </el-form-item>

            <el-form-item>
              <el-checkbox v-model="rememberMe">记住我</el-checkbox>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                native-type="submit"
                :loading="loading"
                size="large"
                class="login-btn"
              >
                {{ loading ? '登录中...' : '登 录' }}
              </el-button>
            </el-form-item>
          </el-form>
        </template>

        <transition name="fade">
          <div v-if="error" class="login-error">
            <el-alert :title="error" type="error" :closable="false" show-icon />
          </div>
        </transition>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, shallowRef, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { User, Lock, Loading, CircleCheckFilled } from '@element-plus/icons-vue'
import api from '../api/index'

const UserIcon = shallowRef(User)
const LockIcon = shallowRef(Lock)

const router = useRouter()
const auth = useAuthStore()
const formRef = ref(null)
const loading = ref(false)
const error = ref('')
const rememberMe = ref(true)
const isReady = ref(false)
const isFirstTime = ref(false)

const form = reactive({
  username: localStorage.getItem('saved_username') || '',
  password: '',
  confirmPassword: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, cb) => {
        if (value !== form.password) cb(new Error('两次密码不一致'))
        else cb()
      },
      trigger: 'blur',
    },
  ],
}

onMounted(async () => {
  if (auth.isLoggedIn) {
    const ok = await auth.checkSession()
    if (ok) {
      router.replace('/')
      return
    }
    auth.logout()
  }

  // 检查系统是否已初始化，决定显示注册还是登录
  try {
    const res = await api.get('/auth/has-users')
    isFirstTime.value = !res.hasUsers
  } catch {
    // 出错时默认显示登录页
  }
  isReady.value = true
})

async function handleRegister() {
  if (loading.value) return
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  error.value = ''
  try {
    await auth.register(form.username, form.password)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || e.response?.data?.error?.message || '注册失败'
  } finally {
    loading.value = false
  }
}

async function handleLogin() {
  if (loading.value) return
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  error.value = ''
  try {
    await auth.login(form.username, form.password)
    if (rememberMe.value) {
      localStorage.setItem('saved_username', form.username)
    } else {
      localStorage.removeItem('saved_username')
    }
    router.push('/')
  } catch (e) {
    const detail = e.response?.data?.detail || e.response?.data?.error?.message || '登录失败，请检查网络连接'
    error.value = detail
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

.login-container {
  width: 420px;
  padding: 20px;
}

.login-brand {
  text-align: center;
  margin-bottom: 32px;
}

.brand-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: 18px;
  background: linear-gradient(135deg, #409EFF, #337ecc);
  color: #fff;
  margin-bottom: 16px;
  box-shadow: 0 8px 24px rgba(64, 158, 255, 0.3);
}

.brand-title {
  font-size: 24px;
  font-weight: 700;
  color: #e8e8e8;
  margin: 0 0 8px 0;
  letter-spacing: 2px;
}

.brand-desc {
  font-size: 14px;
  color: #8899aa;
  margin: 0;
}

.login-card {
  border-radius: 12px;
  background: #1e2a3a !important;
  border: 1px solid #2a3a4a !important;
  padding: 8px 0;
}

.login-card :deep(.el-form-item) {
  margin-bottom: 22px;
}

.login-card :deep(.el-input__wrapper) {
  background: #162030;
  border: 1px solid #2a3a4a;
  border-radius: 8px;
  box-shadow: none;
  padding: 4px 12px;
}

.login-card :deep(.el-input__wrapper:hover) {
  border-color: #409EFF;
}

.login-card :deep(.el-input__wrapper.is-focus) {
  border-color: #409EFF;
  box-shadow: 0 0 0 1px rgba(64, 158, 255, 0.3);
}

.login-card :deep(.el-input__inner) {
  color: #e8e8e8;
  height: 42px;
}

.login-card :deep(.el-input__inner::placeholder) {
  color: #5a6a7a;
}

.login-card :deep(.el-input__prefix) {
  color: #5a6a7a;
}

.login-card :deep(.el-checkbox__label) {
  color: #8899aa;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  letter-spacing: 4px;
  border-radius: 8px;
}

.login-error {
  margin-top: 8px;
}

.login-error :deep(.el-alert) {
  border-radius: 8px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px 0;
  color: #8899aa;
}

.setup-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 0 20px 0;
  border-bottom: 1px solid #2a3a4a;
  margin-bottom: 20px;
}

.setup-title {
  font-size: 18px;
  font-weight: 600;
  color: #e8e8e8;
  margin: 0 0 4px 0;
}

.setup-desc {
  font-size: 13px;
  color: #8899aa;
  margin: 0;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
