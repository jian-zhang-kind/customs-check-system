<template>
  <div class="shell">
    <el-result icon="warning" title="页面没有正常打开" sub-title="可以回到演示入口再试一次。">
      <template #extra>
        <el-button type="primary" @click="handleError">返回演示入口</el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
const handleError = () => clearError({ redirect: "/" })
</script>
