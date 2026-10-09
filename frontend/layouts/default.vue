<template>
  <div class="shell">
    <header class="topbar">
      <div>
        <div class="brand">申报前自查</div>
        <h1>关务慧眼</h1>
      </div>
      <nav class="nav">
        <el-button text @click="goHome">演示入口</el-button>
        <el-button text @click="goCases">票次列表</el-button>
        <el-button text @click="goNew">新建业务票</el-button>
      </nav>
    </header>
    <slot />
    <p class="footnote">
      本系统为竞赛演示工具，输出不构成法律意见或正式归类裁定。锂电池演示不做出口管制筛查，不给出运或危化鉴定。
    </p>
  </div>
</template>

<script setup lang="ts">
function goHome() {
  navigateTo("/")
}

function goCases() {
  navigateTo("/cases")
}

function goNew() {
  navigateTo("/cases/new")
}
</script>
