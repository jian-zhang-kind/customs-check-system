<template>
  <main class="stack">
    <section class="panel stack">
      <p class="lede">
        用一份锂电池出口越南的演示票，查看单单、单证和单货自查结果。这一步只生成演示票，不会建立业务空票。
      </p>
      <div>
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          :disabled="loading"
          @click="startDemo"
        >
          一键演示（锂电池出口越南）
        </el-button>
      </div>
      <el-alert
        v-if="errorText"
        :title="errorText"
        type="error"
        show-icon
        :closable="false"
      />
      <div v-if="errorText">
        <el-button :disabled="loading" @click="startDemo">重新生成演示</el-button>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { messageFromError, saveDemoResult, useCheckApi } from "~/composables/useCheckApi"

const api = useCheckApi()
const loading = ref(false)
const errorText = ref("")

async function startDemo() {
  if (loading.value) {
    return
  }
  loading.value = true
  errorText.value = ""
  try {
    const data = await api.loadDemo()
    saveDemoResult(data)
    await navigateTo(`/cases/${data.case_id}`)
  } catch (error) {
    errorText.value = messageFromError(error).text
  } finally {
    loading.value = false
  }
}
</script>
