<template>
  <section class="panel stack">
    <h2>上传资料</h2>
    <p class="lede">上传不会自动开始校验。需要在下方手动点击开始校验。</p>
    <el-alert v-if="errorText" :title="errorText" type="error" show-icon :closable="false" />

    <div class="upload-grid">
      <div v-for="slot in documentSlots" :key="slot.docType" class="upload-slot stack">
        <strong>{{ slot.label }}</strong>
        <span class="lede">pdf / png / jpg，不超过 8MB</span>
        <el-upload
          :show-file-list="false"
          :disabled="disabled || uploading === `doc:${slot.docType}`"
          accept=".pdf,.png,.jpg,.jpeg"
          :before-upload="guardDocument"
          :http-request="(options) => sendDocument(slot.docType, options)"
        >
          <el-button :loading="uploading === `doc:${slot.docType}`" :disabled="disabled">上传{{ slot.label }}</el-button>
        </el-upload>
      </div>
      <div v-for="slot in photoSlots" :key="slot.kind" class="upload-slot stack">
        <strong>{{ slot.label }}</strong>
        <span class="lede">png / jpg，不超过 8MB</span>
        <el-upload
          :show-file-list="false"
          :disabled="disabled || uploading === `photo:${slot.kind}`"
          accept=".png,.jpg,.jpeg"
          :before-upload="guardPhoto"
          :http-request="(options) => sendPhoto(slot.kind, options)"
        >
          <el-button :loading="uploading === `photo:${slot.kind}`" :disabled="disabled">上传{{ slot.label }}</el-button>
        </el-upload>
      </div>
    </div>

    <el-table v-loading="loading" :data="rows" empty-text="还没有上传资料">
      <el-table-column prop="filename" label="文件名" min-width="220" />
      <el-table-column prop="typeLabel" label="类型" width="140" />
      <el-table-column prop="created_at" label="上传时间" min-width="180" />
    </el-table>
  </section>
</template>

<script setup lang="ts">
import { messageFromError, useCheckApi } from "~/composables/useCheckApi"
import type { DocType, PhotoKind } from "~/types/api"
import { validateUpload } from "~/utils/files"

interface UploadRequest {
  file: File
  onSuccess: (response: unknown) => void
  onError: (error: Error) => void
}

const props = defineProps<{
  caseId: number
  disabled: boolean
}>()

const emit = defineEmits<{
  changed: []
}>()

const api = useCheckApi()
const loading = ref(false)
const uploading = ref("")
const errorText = ref("")
const rows = ref<Array<{ filename: string; typeLabel: string; created_at: string }>>([])

const documentSlots: Array<{ docType: DocType; label: string }> = [
  { docType: "declaration", label: "报关单" },
  { docType: "invoice", label: "商业发票" },
  { docType: "packing", label: "装箱单" },
  { docType: "contract", label: "合同" },
]

const photoSlots: Array<{ kind: PhotoKind; label: string }> = [
  { kind: "mark", label: "唛头" },
  { kind: "packing", label: "现场箱单" },
]

const typeLabels: Record<string, string> = {
  declaration: "报关单",
  invoice: "商业发票",
  packing: "装箱单",
  contract: "合同",
  mark: "唛头",
  "photo-packing": "现场箱单",
}

function guard(file: File, group: "document" | "photo") {
  const problem = validateUpload(file, group)
  errorText.value = problem || ""
  return !problem
}

function guardDocument(file: File) {
  return guard(file, "document")
}

function guardPhoto(file: File) {
  return guard(file, "photo")
}

async function reload() {
  loading.value = true
  try {
    const [documents, photos] = await Promise.all([
      api.listDocuments(props.caseId),
      api.listPhotos(props.caseId),
    ])
    rows.value = [
      ...documents.list.map((item) => ({
        filename: item.filename,
        typeLabel: typeLabels[item.doc_type],
        created_at: item.created_at,
      })),
      ...photos.list.map((item) => ({
        filename: item.filename,
        typeLabel: item.kind === "packing" ? typeLabels["photo-packing"] : typeLabels[item.kind],
        created_at: item.created_at,
      })),
    ]
  } catch (error) {
    errorText.value = messageFromError(error, "资料列表加载失败，请重试").text
  } finally {
    loading.value = false
  }
}

async function sendDocument(docType: DocType, options: UploadRequest) {
  uploading.value = `doc:${docType}`
  errorText.value = ""
  try {
    const saved = await api.uploadDocument(props.caseId, docType, options.file)
    options.onSuccess(saved)
    await reload()
    emit("changed")
  } catch (error) {
    errorText.value = messageFromError(error, "上传失败，请重试").text
    options.onError(error instanceof Error ? error : new Error(errorText.value))
  } finally {
    uploading.value = ""
  }
}

async function sendPhoto(kind: PhotoKind, options: UploadRequest) {
  uploading.value = `photo:${kind}`
  errorText.value = ""
  try {
    const saved = await api.uploadPhoto(props.caseId, kind, options.file)
    options.onSuccess(saved)
    await reload()
    emit("changed")
  } catch (error) {
    errorText.value = messageFromError(error, "上传失败，请重试").text
    options.onError(error instanceof Error ? error : new Error(errorText.value))
  } finally {
    uploading.value = ""
  }
}

onMounted(reload)
</script>
