<template>
  <main class="stack">
    <el-alert v-if="pageError" :title="pageError" type="error" show-icon :closable="false" />

    <section v-if="caseInfo" class="panel stack">
      <div class="meta">
        <el-tag v-if="caseInfo.is_demo" type="success">演示票</el-tag>
        <el-tag v-else type="info">业务票</el-tag>
        <el-tag>{{ caseInfo.case_no }}</el-tag>
        <el-tag :type="statusTag">状态 {{ caseInfo.status }}</el-tag>
        <span class="lede">目的国 {{ caseInfo.destination_country || "未填写" }}</span>
      </div>
      <h2>{{ caseInfo.title || caseInfo.case_no }}</h2>
      <p v-if="caseInfo.remark" class="lede">{{ caseInfo.remark }}</p>
      <div v-if="caseInfo.is_demo && caseInfo.status === 'failed'">
        <el-alert title="演示生成失败，请重试" type="error" show-icon :closable="false" />
        <el-button type="primary" :loading="retrying" @click="retryDemo">重新生成演示</el-button>
      </div>
    </section>

    <CaseMaterials
      v-if="caseInfo && !caseInfo.is_demo"
      :case-id="caseInfo.id"
      :disabled="running || caseInfo.status === 'running'"
      @changed="refreshCase"
    />

    <section v-if="caseInfo && !caseInfo.is_demo" class="panel stack">
      <p v-if="caseInfo.status === 'running'" class="lede">票次正在校验，不能重复触发。</p>
      <p v-else-if="caseInfo.status === 'failed'" class="lede">校验失败，可以直接重新校验。</p>
      <div>
        <el-button
          type="primary"
          size="large"
          :loading="running"
          :disabled="running || confirming || caseInfo.status === 'running'"
          @click="startRun"
        >
          {{ runLabel }}
        </el-button>
      </div>
    </section>

    <CaseReport
      v-if="showFindings"
      :report="report"
      :risk-items="riskItems"
      :graph-edges="graphEdges"
      :risk-error="riskError"
      :graph-error="graphError"
      :risk-loading="riskLoading"
      :graph-loading="graphLoading"
      :refreshing="refreshing"
      @refresh="refreshReport"
    />
  </main>
</template>

<script setup lang="ts">
import { ElMessageBox } from "element-plus"
import CaseMaterials from "~/components/CaseMaterials.vue"
import CaseReport from "~/components/CaseReport.vue"
import { messageFromError, readDemoResult, saveDemoResult, useCheckApi } from "~/composables/useCheckApi"
import type { CaseInfo, Hyperedge, ReportSummary, RiskItem } from "~/types/api"

const route = useRoute()
const api = useCheckApi()
const caseId = computed(() => Number(route.params.id))

const caseInfo = ref<CaseInfo | null>(null)
const report = ref<ReportSummary | null>(null)
const riskItems = ref<RiskItem[]>([])
const graphEdges = ref<Hyperedge[]>([])
const pageError = ref("")
const riskError = ref("")
const graphError = ref("")
const riskLoading = ref(false)
const graphLoading = ref(false)
const refreshing = ref(false)
const retrying = ref(false)
const running = ref(false)
const confirming = ref(false)

const statusTag = computed(() => {
  if (caseInfo.value?.status === "failed") return "danger"
  if (caseInfo.value?.status === "completed") return "success"
  return "info"
})

const showFindings = computed(() => Boolean(caseInfo.value?.is_demo || report.value))

const runLabel = computed(() => {
  if (caseInfo.value?.status === "completed" || caseInfo.value?.status === "failed") return "重新校验"
  return "开始校验"
})

async function loadSupplements() {
  riskLoading.value = true
  graphLoading.value = true
  riskError.value = ""
  graphError.value = ""
  const [riskResult, graphResult] = await Promise.allSettled([
    api.getRiskItems(caseId.value),
    api.getHypergraph(caseId.value),
  ])
  riskLoading.value = false
  graphLoading.value = false
  if (riskResult.status === "fulfilled") {
    riskItems.value = riskResult.value.list
  } else {
    riskError.value = messageFromError(riskResult.reason).text
  }
  if (graphResult.status === "fulfilled") {
    graphEdges.value = graphResult.value.edges
  } else {
    graphError.value = messageFromError(graphResult.reason).text
  }
}

async function refreshCase() {
  try {
    caseInfo.value = await api.getCase(caseId.value)
  } catch (error) {
    pageError.value = messageFromError(error, "票次加载失败，请重试").text
  }
}

async function refreshReport() {
  refreshing.value = true
  pageError.value = ""
  try {
    const [nextCase, nextReport] = await Promise.all([
      api.getCase(caseId.value),
      api.getReport(caseId.value),
    ])
    caseInfo.value = nextCase
    report.value = nextReport
  } catch (error) {
    pageError.value = messageFromError(error, "报告加载失败，请重试").text
  } finally {
    refreshing.value = false
  }
}

async function retryDemo() {
  retrying.value = true
  pageError.value = ""
  try {
    const data = await api.loadDemo()
    saveDemoResult(data)
    await navigateTo(`/cases/${data.case_id}`)
  } catch (error) {
    pageError.value = messageFromError(error).text
  } finally {
    retrying.value = false
  }
}

async function startRun() {
  if (!caseInfo.value || running.value || confirming.value) {
    return
  }
  if (caseInfo.value.status === "running") {
    pageError.value = "票次正在校验，不能重复触发"
    return
  }
  const force = caseInfo.value.status === "completed"
  if (force) {
    confirming.value = true
    try {
      await ElMessageBox.confirm("再次校验会覆盖当前报告、风险项和字段勾稽。", "确认重新校验", {
        confirmButtonText: "重新校验",
        cancelButtonText: "取消",
        type: "warning",
      })
    } catch {
      return
    } finally {
      confirming.value = false
    }
  }
  running.value = true
  pageError.value = ""
  try {
    const data = await api.runCase(caseInfo.value.id, force)
    report.value = data.report
    caseInfo.value = await api.getCase(caseInfo.value.id)
    await loadSupplements()
  } catch (error) {
    const parsed = messageFromError(error, "校验失败，请重试")
    pageError.value = parsed.text === "无可校验材料" ? "请先上传单据或现场照片" : parsed.text
    await refreshCase()
  } finally {
    running.value = false
  }
}

onMounted(async () => {
  if (!Number.isInteger(caseId.value) || caseId.value <= 0) {
    pageError.value = "票次编号无效"
    return
  }
  const cached = readDemoResult(caseId.value)
  if (cached) {
    caseInfo.value = cached.case
    report.value = cached.report
    await loadSupplements()
    return
  }
  try {
    caseInfo.value = await api.getCase(caseId.value)
  } catch (error) {
    pageError.value = messageFromError(error, "票次加载失败，请重试").text
    return
  }
  try {
    report.value = await api.getReport(caseId.value)
  } catch (error) {
    const parsed = messageFromError(error, "报告加载失败，请重试")
    if (parsed.status !== 404) {
      pageError.value = parsed.text
    }
  }
  if (caseInfo.value.is_demo || report.value) {
    await loadSupplements()
  }
})
</script>
