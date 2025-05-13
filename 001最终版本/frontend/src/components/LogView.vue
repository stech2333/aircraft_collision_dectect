<template>
  <div class="log-container">
    <div class="log-header">
      <h2>碰撞风险检测日志</h2>
      <button @click="$router.push('/')" class="back-btn">返回地图</button>
    </div>
    
    <div class="log-panel">
      <div class="log-list">
        <div v-show="logs.length === 0" class="empty-message">
          暂无日志记录
        </div>
        <div v-for="log in logs" 
             :key="log.filename" 
             :class="['log-item', {'selected': selectedLog === log.filename}]"
             @click="selectLog(log.filename)">
          <div class="log-info">
            <div class="log-time">{{ log.timestamp }}</div>
            <div class="log-size">{{ formatSize(log.size) }}</div>
          </div>
        </div>
      </div>
      
      <div v-if="error" class="error-message">
        {{ error }}
      </div>
      
      <div class="log-content" v-else-if="logContent">
        <pre>{{ logContent }}</pre>
      </div>
      <div v-else class="no-content">
        请选择左侧日志文件查看详细内容
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'LogView',
  data() {
    return {
      logs: [],
      selectedLog: null,
      logContent: null,
      error: null
    }
  },
  created() {
    this.loadLogs()
  },
  methods: {
    async loadLogs() {
      try {
        this.error = null
        this.logs = []
        
        console.log('开始加载日志列表') // 调试信息
        const response = await axios.get('http://localhost:5000/api/logs/list')
        console.log('日志列表响应:', response.data) // 调试信息
        
        if (Array.isArray(response.data)) {
          this.logs = response.data
          if (this.logs.length > 0) {
            await this.selectLog(this.logs[0].filename)
          }
        } else {
          throw new Error('返回数据格式错误')
        }
      } catch (error) {
        console.error('加载日志列表失败:', error)
        this.error = '加载日志列表失败，请刷新页面重试。错误信息：' + error.message
      }
    },
    
    async selectLog(filename) {
      try {
        this.error = null
        this.logContent = null
        this.selectedLog = filename
        
        console.log('开始加载日志内容:', filename) // 调试信息
        const response = await axios.get(`http://localhost:5000/api/logs/${filename}`)
        console.log('日志内容响应:', response.data) // 调试信息
        
        if (response.data && response.data.content) {
          this.logContent = response.data.content
        } else {
          throw new Error('返回数据格式错误')
        }
      } catch (error) {
        console.error('加载日志内容失败:', error)
        this.error = '加载日志内容失败，请重试'
        this.selectedLog = null
      }
    },
    formatSize(bytes) {
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    }
  }
}
</script>

<style scoped>
.log-container {
  padding: 20px;
  height: calc(100vh - 60px);
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.back-btn {
  background: #1890ff;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.log-panel {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 20px;
  height: calc(100% - 60px);
  background: white;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.log-list {
  border-right: 1px solid #eee;
  overflow-y: auto;
}

.log-item {
  padding: 15px;
  cursor: pointer;
  border-bottom: 1px solid #eee;
  transition: all 0.3s;
}

.log-item:hover {
  background: #f5f5f5;
}

.log-item.selected {
  background: #e6f7ff;
  border-right: 2px solid #1890ff;
}

.log-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.log-time {
  font-weight: bold;
  color: #1890ff;
}

.log-size {
  color: #666;
  font-size: 0.9em;
}

.log-content {
  padding: 20px;
  overflow-y: auto;
  background: #fafafa;
  border-radius: 4px;
}

.log-content pre {
  margin: 0;
  white-space: pre-wrap;
  font-family: monospace;
  line-height: 1.5;
}

.no-content {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #999;
  font-size: 16px;
}

.empty-message,
.error-message {
  padding: 20px;
  text-align: center;
  color: #999;
}

.error-message {
  color: #ff4d4f;
}
</style>
