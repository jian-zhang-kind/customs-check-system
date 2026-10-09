<template>
  <article class="stack">
    <h3>{{ title }}</h3>
    <template v-if="rule">
      <div class="meta">
        <el-tag>{{ rule.rule_id }}</el-tag>
        <el-tag :type="verdictTag">verdict {{ rule.verdict }}</el-tag>
        <el-tag type="info">rule_outcome {{ rule.rule_outcome }}</el-tag>
      </div>
      <p v-if="rule.description">{{ rule.description }}</p>
      <p class="lede">{{ rule.regulation_name || "无法规名称" }}</p>
      <p class="lede">发布日期 {{ rule.publish_date || "无" }}</p>
      <p v-if="rule.source_url">
        <a :href="rule.source_url" target="_blank" rel="noopener">{{ rule.source_url }}</a>
      </p>
      <p v-else class="lede">无来源链接</p>
      <p v-if="rule.excerpt" class="excerpt">{{ rule.excerpt }}</p>
    </template>
    <p v-else class="lede">接口未返回这条 HS 结论。</p>
  </article>
</template>

<script setup lang="ts">
import type { HsRuleView } from "~/types/api"

const props = defineProps<{
  title: string
  rule: HsRuleView | null
}>()

const verdictTag = computed(() => {
  if (props.rule?.verdict === "fail") return "danger"
  if (props.rule?.verdict === "warning") return "warning"
  if (props.rule?.verdict === "pass") return "success"
  return "info"
})
</script>
