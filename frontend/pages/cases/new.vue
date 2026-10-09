<template>
  <main class="stack">
    <section class="panel stack">
      <h2>新建业务票</h2>
      <p class="lede">只建立一张空票。这一步不上传文件，也不开始校验。</p>
      <el-alert v-if="errorText" :title="errorText" type="error" show-icon :closable="false" />
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="票号 case_no" required>
          <el-input v-model="form.case_no" placeholder="例如 CK-2026-0001" />
        </el-form-item>
        <el-form-item label="标题 title">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="目的国 destination_country">
          <el-input v-model="form.destination_country" placeholder="例如 VN" />
        </el-form-item>
        <el-form-item label="备注 remark">
          <el-input v-model="form.remark" type="textarea" :rows="3" />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" :disabled="loading">建立空票</el-button>
      </el-form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { messageFromError, useCheckApi } from "~/composables/useCheckApi"

const api = useCheckApi()
const loading = ref(false)
const errorText = ref("")
const form = reactive({
  case_no: "",
  title: "",
  destination_country: "",
  remark: "",
})

async function submit() {
  if (loading.value) {
    return
  }
  if (!form.case_no.trim()) {
    errorText.value = "case_no 不能为空"
    return
  }
  loading.value = true
  errorText.value = ""
  try {
    const created = await api.createCase({
      case_no: form.case_no,
      title: form.title,
      destination_country: form.destination_country,
      remark: form.remark,
    })
    await navigateTo(`/cases/${created.id}`)
  } catch (error) {
    errorText.value = messageFromError(error, "建票失败，请重试").text
  } finally {
    loading.value = false
  }
}
</script>
