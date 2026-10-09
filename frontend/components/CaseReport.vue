<template>
  <div class="stack">
    <section v-if="report" class="panel stack">
      <div class="meta">
        <strong>总判定</strong>
        <el-tag :type="verdictTag(report.summary_verdict)">{{ report.summary_verdict }}</el-tag>
        <span class="lede">生成时间 {{ report.created_at }}</span>
        <el-button :loading="refreshing" @click="emit('refresh')">刷新报告</el-button>
      </div>
      <div class="hs-grid">
        <HsPanel title="中国 HS" :rule="report.hs_cn" />
        <HsPanel title="目的国 HS" :rule="report.hs_dest" />
      </div>
      <p v-if="report.disclaimer" class="lede">{{ report.disclaimer }}</p>
    </section>

    <section class="panel stack">
      <h2>风险项</h2>
      <el-alert v-if="riskError" :title="riskError" type="error" show-icon :closable="false" />
      <el-table v-loading="riskLoading" :data="riskItems" empty-text="暂无风险项">
        <el-table-column prop="rule_id" label="规则" width="120" />
        <el-table-column prop="risk_level" label="风险等级" width="120" />
        <el-table-column prop="verdict" label="判定" width="110" />
        <el-table-column prop="rule_outcome" label="规则结果" width="180" />
        <el-table-column prop="description" label="问题描述" min-width="240" />
        <el-table-column label="法规来源" min-width="180">
          <template #default="{ row }">
            <a v-if="row.source_url" :href="row.source_url" target="_blank" rel="noopener">{{ row.source_url }}</a>
            <span v-else>无来源</span>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="panel stack">
      <h2>字段勾稽</h2>
      <p class="lede">这里只接入超图快照。快照里没有判定，对错看上面的风险项。</p>
      <el-alert v-if="graphError" :title="graphError" type="error" show-icon :closable="false" />
      <el-table v-loading="graphLoading" :data="graphEdges" empty-text="暂无超边">
        <el-table-column prop="rule_id" label="规则" width="120" />
        <el-table-column prop="constraint_type" label="约束类型" width="180" />
        <el-table-column label="成员槽位" min-width="280">
          <template #default="{ row }">
            {{ row.members.map((member) => member.slot_name).join("，") }}
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import HsPanel from "~/components/HsPanel.vue"
import type { Hyperedge, ReportSummary, RiskItem, Verdict } from "~/types/api"

defineProps<{
  report: ReportSummary | null
  riskItems: RiskItem[]
  graphEdges: Hyperedge[]
  riskError: string
  graphError: string
  riskLoading: boolean
  graphLoading: boolean
  refreshing: boolean
}>()

const emit = defineEmits<{
  refresh: []
}>()

function verdictTag(verdict: Verdict | null) {
  if (verdict === "fail") return "danger"
  if (verdict === "warning") return "warning"
  if (verdict === "pass") return "success"
  return "info"
}
</script>
