<template>
  <div class="history-container">
    <div class="history-header">
      <h2>无人机历史轨迹</h2>
      <div class="drone-info">
        <p><strong>序列号:</strong> {{ serial }}</p>
      </div>
      <button @click="$router.back()" class="back-btn">返回列表</button>
    </div>
    
    <el-table 
      :data="trajectoryData" 
      style="width: 100%"
      :default-sort = "{prop: 'timestamp', order: 'descending'}"
      >
      <el-table-column 
        prop="timestamp" 
        label="时间" 
        sortable
        :formatter="formatTime">
      </el-table-column>
      <el-table-column 
        prop="lat" 
        label="纬度"
        :formatter="formatCoordinate">
      </el-table-column>
      <el-table-column 
        prop="lng" 
        label="经度"
        :formatter="formatCoordinate">
      </el-table-column>
      <el-table-column 
        prop="z" 
        label="高度(米)">
      </el-table-column>
      <el-table-column 
        label="速度(m/s)"
        :formatter="formatSpeed">
      </el-table-column>
    </el-table>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'DroneHistory',
  data() {
    return {
      serial: this.$route.params.serial,
      trajectoryData: []
    }
  },
  created() {
    this.loadTrajectoryData()
  },
  methods: {
    async loadTrajectoryData() {
      try {
        const response = await axios.get(`http://localhost:5000/api/drone/${this.serial}/trajectory`)
        this.trajectoryData = response.data
      } catch (error) {
        console.error('加载轨迹数据失败:', error)
      }
    },
    formatTime(row) {
      return new Date(row.timestamp).toLocaleString()
    },
    formatCoordinate(row, column) {
      const value = row[column.property]
      return value.toFixed(6) + '°'
    },
    formatSpeed(row) {
      const speed = Math.sqrt(
        (row.vx || 0) ** 2 + 
        (row.vy || 0) ** 2 + 
        (row.vz || 0) ** 2
      )
      return speed.toFixed(2)
    }
  }
}
</script>

<style scoped>
.history-container {
  padding: 20px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.drone-info {
  text-align: center;
}

.back-btn {
  background: #1890ff;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.back-btn:hover {
  background: #40a9ff;
}
</style>
