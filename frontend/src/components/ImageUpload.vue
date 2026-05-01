<template>
  <div class="image-upload">
    <!-- 有recordId时可上传，无recordId时提示先保存 -->
    <div v-if="recordId > 0" style="display:flex;align-items:flex-start;gap:8px;">
      <el-upload
        :show-file-list="false"
        :before-upload="beforeUpload"
        :http-request="handleUpload"
        accept="image/jpeg,image/png,image/gif,image/webp"
      >
        <el-button type="primary" size="small" :loading="uploading">
          {{ imageUrl ? '换图' : '选择图片' }}
        </el-button>
      </el-upload>
      <el-button v-if="imageUrl" type="danger" size="small" @click="handleRemove">删图</el-button>
    </div>
    <div v-else style="color:var(--el-text-color-secondary);font-size:12px;">
      保存记录后可上传附件图片
    </div>
    <div v-if="imageUrl" style="margin-top:8px;">
      <el-image
        :src="resolveUrl(imageUrl)"
        style="max-width:200px;max-height:150px;"
        fit="contain"
        :preview-src-list="[resolveUrl(imageUrl)]"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const API_BASE = 'http://localhost:8000'

const props = defineProps({
  modelValue: { type: String, default: '' },
  businessType: { type: String, default: 'expense' },
  recordId: { type: Number, default: 0 },
  updateApi: { type: Function, default: null }
})
const emit = defineEmits(['update:modelValue'])

const imageUrl = ref(props.modelValue)
const uploading = ref(false)

watch(() => props.modelValue, (val) => { imageUrl.value = val })

const resolveUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `${API_BASE}${url}`
}

const beforeUpload = (file) => {
  const isImage = file.type.startsWith('image/')
  if (!isImage) { ElMessage.error('只能上传图片文件!'); return false }
  const isLt5M = file.size / 1024 / 1024 < 5
  if (!isLt5M) { ElMessage.error('图片不能超过5MB!'); return false }
  return true
}

const handleUpload = async ({ file }) => {
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)

    let res
    if (imageUrl.value) {
      // 换图
      res = await api.replaceImage(formData, props.businessType, props.recordId, imageUrl.value)
    } else {
      // 新上传
      res = await api.uploadImage(formData, props.businessType, props.recordId)
    }
    imageUrl.value = res.image_url
    emit('update:modelValue', res.image_url)

    // 自动保存到数据库（如果有updateApi）
    if (props.updateApi && props.recordId > 0) {
      try {
        await props.updateApi(props.recordId, { image_url: res.image_url })
      } catch (e) {
        ElMessage.warning('图片已上传，但保存到数据库失败，请手动保存')
      }
    }

    ElMessage.success('上传成功')
  } catch (e) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

const handleRemove = async () => {
  try {
    if (imageUrl.value) {
      await api.deleteImage(resolveUrl(imageUrl.value))
    }
  } catch (e) { /* 即使删文件失败也清空URL */ }
  const oldUrl = imageUrl.value
  imageUrl.value = ''
  emit('update:modelValue', '')

  // 自动从数据库清除
  if (props.updateApi && props.recordId > 0) {
    try {
      await props.updateApi(props.recordId, { image_url: '' })
    } catch (e) {
      ElMessage.warning('图片已删除，但数据库更新失败，请手动保存')
    }
  }
  ElMessage.success('已删除')
}
</script>