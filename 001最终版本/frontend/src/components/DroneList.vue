<template>
  <div class="drone-list-container">
    <div class="header">
      <h1>无人机列表</h1>
      <button @click="goBack" class="back-btn">返回地图</button>
    </div>
    <el-table 
      :data="drones"
      @row-click="handleRowClick"
      style="width: 100%">
      <el-table-column label="序列号" prop="serial"/>
      <el-table-column label="纬度" prop="lat">
        <template #default="scope">
          {{ scope.row.lat ? scope.row.lat.toFixed(6) + '°N' : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="经度" prop="lng">
        <template #default="scope">
          {{ scope.row.lng ? scope.row.lng.toFixed(6) + '°E' : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="高度" prop="z">
        <template #default="scope">
          {{ scope.row.z ? scope.row.z + '米' : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="水平速度">
        <template #default="scope">
          {{ calculateHorizontalSpeed(scope.row).toFixed(2) }} m/s
        </template>
      </el-table-column>
      <el-table-column label="垂直速度" prop="vz">
        <template #default="scope">
          {{ scope.row.vz ? scope.row.vz.toFixed(2) + ' m/s' : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="最后更新时间" prop="last_updated">
        <template #default="scope">
          {{ new Date(scope.row.last_updated).toLocaleString() }}
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'DroneList',
  data() {
    return {
      drones: []
    }
  },
  mounted() {
    this.loadDrones()
    // 每秒更新一次数据
    this.updateInterval = setInterval(this.loadDrones, 1000)
  },
  beforeUnmount() {
    // 组件销毁前清除定时器
    if (this.updateInterval) {
      clearInterval(this.updateInterval)
    }
  },
  methods: {
    async loadDrones() {
      try {
        const response = await axios.get('http://localhost:5000/api/db/drones/current')
        this.drones = response.data
      } catch (error) {
        console.error('加载无人机数据失败:', error)
      }
    },
    calculateHorizontalSpeed(drone) {
      return Math.sqrt((drone.vx || 0)**2 + (drone.vy || 0)**2)
    },
    goBack() {
      this.$router.push('/')
    },
    handleRowClick(row) {
      this.$router.push(`/drone/${row.serial}/history`)
    }
  }
}
</script>

<style scoped>
.drone-list-container {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

h1 {
  margin: 0;
  color: #1890ff;
}

.back-btn {
  background: #1890ff;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.3s;
}

.back-btn:hover {
  background: #40a9ff;
  transform: translateY(-2px);
}
</style>
