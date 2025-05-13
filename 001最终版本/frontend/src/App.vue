<template>
  <div class="app-container">
    <el-container>
      <el-header>
        <h1>无人机监控系统</h1>
      </el-header>
      <el-main>
        <router-view></router-view>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
// 组件逻辑
</script>

<style>
.app-container {
  height: 100vh;
  width: 100vw;
}

.el-header {
  background-color: #409EFF;
  color: white;
  text-align: center;
  line-height: 60px;
}

.el-main {
  padding: 0;
  height: calc(100vh - 60px);
}
</style> 