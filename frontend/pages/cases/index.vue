<template>
  <main class="stack">
    <section class="panel stack">
      <div class="meta">
        <h2>票次列表</h2>
        <el-button type="primary" @click="goNew">新建业务票</el-button>
      </div>
      <div class="meta">
        <el-select v-model="status" placeholder="状态" style="width: 160px" @change="applyFilter">
          <el-option label="全部状态" value="" />
          <el-option label="pending" value="pending" />
          <el-option label="running" value="running" />
          <el-option label="completed" value="completed" />
          <el-option label="failed" value="failed" />
        </el-select>
        <el-select v-model="demoFilter" placeholder="票种" style="width: 160px" @change="applyFilter">
          <el-option label="全部票" value="" />
          <el-option label="业务票" value="false" />
          <el-option label="演示票" value="true" />
        </el-select>
      </div>
      <el-alert v-if="errorText" :title="errorText" type="error" show-icon :closable="false" />
      <el-table v-loading="loading" :data="rows" empty-text="暂无票次">
        <el-table-column prop="case_no" label="票号" min-width="180" />
        <el-table-column prop="title" label="标题" min-width="180" />
        <el-table-column label="标记" width="110">
          <template #default="{ row }">
            <el-tag :type="row.is_demo ? 'success' : 'info'">{{ row.is_demo ? "演示票" : "业务票" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="destination_country" label="目的国" width="100" />
        <el-table-column prop="created_at" label="创建时间" min-width="180" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button text @click="openCase(row.id)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="load"
      />
    </section>
  </main>
</template>

<script setup lang="ts">
import { messageFromError, useCheckApi } from "~/composables/useCheckApi"
import type { CaseInfo, CaseStatus } from "~/types/api"

const api = useCheckApi()
const loading = ref(false)
const errorText = ref("")
const rows = ref<CaseInfo[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const status = ref<CaseStatus | "">("")
const demoFilter = ref<"" | "true" | "false">("")

function goNew() {
  navigateTo("/cases/new")
}

function openCase(id: number) {
  navigateTo(`/cases/${id}`)
}

function applyFilter() {
  page.value = 1
  load()
}

async function load() {
  loading.value = true
  errorText.value = ""
  try {
    const data = await api.listCases({
      page: page.value,
      page_size: pageSize,
      status: status.value || undefined,
      is_demo: demoFilter.value === "" ? undefined : demoFilter.value === "true",
    })
    rows.value = data.list
    total.value = data.total
  } catch (error) {
    errorText.value = messageFromError(error, "票次列表加载失败，请重试").text
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
