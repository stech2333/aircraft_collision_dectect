<template>
  <div class="map-container">
    <div id="map-container"></div>
    <div class="view-list-btn">
      <button @click="viewDroneList" class="list-btn">📋 查看所有无人机</button>
    </div>
    <div class="view-logs-btn">
      <button @click="viewLogs" class="logs-btn">📋 查看碰撞日志</button>
    </div>
    <div class="control-panel">
      <div class="collision-panel">
        <div class="collision-summary">
          <h3>碰撞风险概览</h3>
          <p>当前风险数: {{ alertCount }}</p>
          <p>高风险: {{ highRiskCount }}</p>
          <p>中风险: {{ mediumRiskCount }}</p>
        </div>
        <button @click="checkCollisions" :disabled="collisionChecking" class="collision-check-btn">
          {{ collisionChecking ? '检测中...' : '⚠️ 检查碰撞风险' }}
        </button>
        <div ref="collisionResults" class="collision-results"></div>
      </div>
    </div>
    <div class="search-panel">
      <input type="text" 
             class="search-input" 
             placeholder="输入无人机序列号(多个序列号用逗号分隔)" 
             v-model="searchQuery"
             @keyup="handleSearch">
      <div class="search-results">
        <div v-for="drone in searchResults" 
             :key="drone.serial" 
             class="search-item"
             @click="focusOnDrone(drone)">
          <p><strong>序列号:</strong> {{drone.serial}}</p>
          <p v-if="drone.lat && drone.lng">
            <strong>位置:</strong> {{drone.lat.toFixed(6)}}°N, {{drone.lng.toFixed(6)}}°E
          </p>
          <p v-else><strong>位置:</strong> 暂无位置信息</p>
          <p><strong>高度:</strong> {{drone.z || 0}}米</p>
          <p><strong>最后更新:</strong> {{new Date(drone.last_updated).toLocaleString()}}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'MapView',
  data() {
    return {
      map: null,
      droneMarkers: {},
      currentInfoWindow: null,
      historyPolyline: null,
      searchQuery: '',
      lastSearchTime: 0,
      alertCount: 0,
      highRiskCount: 0,
      mediumRiskCount: 0,
      collisionChecking: false,
      searchResults: [],
      searchTimeout: null,
      updateInterval: null, // 添加定时器引用
      apiBaseUrl: 'http://localhost:5000' // 添加API基础URL
    }
  },
  mounted() {
    this.initMap();
  },
  beforeDestroy() {
    // 组件销毁前清理定时器
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
    }
  },
  methods: {
    initMap() {
      this.map = new BMapGL.Map("map-container")
      const centerPoint = new BMapGL.Point(118.796877, 32.060255)
      this.map.centerAndZoom(centerPoint, 13)
      this.map.enableScrollWheelZoom()
      this.map.setTilt(60)
      this.map.setDisplayOptions({ building: true })

      // 地图点击事件
      this.map.addEventListener('click', () => {
        if (this.historyPolyline) {
          this.map.removeOverlay(this.historyPolyline)
          this.historyPolyline = null
        }
      })

      // 修改定时器的设置方式
      this.updateInterval = setInterval(this.updateDronesPosition, 1000);
      this.updateDronesPosition()
    },

    async updateDronesPosition() {
      try {
        const response = await axios.get(`${this.apiBaseUrl}/api/db/drones/current`);
        const drones = response.data;
        
        for (const drone of drones) {
          if (!drone.lat || !drone.lng) continue;
          
          const point = new BMapGL.Point(drone.lng, drone.lat);
          
          if (!this.droneMarkers[drone.serial]) {
            const marker = new BMapGL.Marker(point);
            // 使用箭头函数以保持this上下文
            marker.addEventListener('click', () => {
              this.showDroneInfo(drone, point);
            });
            this.map.addOverlay(marker);
            this.droneMarkers[drone.serial] = marker;
          } else {
            this.droneMarkers[drone.serial].setPosition(point);
          }
        }
      } catch (error) {
        console.error('更新失败:', error)
      }
    },

    async showserialhistory(serial) {
      try {
        // 如果已有历史轨迹，先清除
        if (this.historyPolyline) {
          this.map.removeOverlay(this.historyPolyline);
          this.historyPolyline = null;
        }

        console.log(`开始加载无人机 ${serial} 的历史轨迹`); // 调试日志
        const response = await axios.get(`${this.apiBaseUrl}/api/drone/${serial}/trajectory`);
        const trajectory = response.data;

        if (trajectory && trajectory.length > 0) {
          console.log(`获取到 ${trajectory.length} 条轨迹记录`); // 调试日志
          
          // 数据验证
          const validPoints = trajectory.filter(point => {
            if (!point.lat || !point.lng) {
              console.log(`无效的轨迹点: ${JSON.stringify(point)}`); // 调试日志
              return false;
            }
            return true;
          });
          
          if (validPoints.length === 0) {
            console.log('没有有效的轨迹点');
            return;
          }
          
          console.log(`有效轨迹点数量: ${validPoints.length}`); // 调试日志
          
          // 创建轨迹点数组
          const points = validPoints.map(point => {
            console.log(`轨迹点: (${point.lng}, ${point.lat})`); // 调试日志
            return new BMapGL.Point(point.lng, point.lat);
          });

          // 创建折线对象
          this.historyPolyline = new BMapGL.Polyline(points, {
            strokeColor: "#1890ff",
            strokeWeight: 4,
            strokeOpacity: 0.8,
            enableMassClear: false
          });

          // 添加到地图
          this.map.addOverlay(this.historyPolyline);
          
          // 调整视图以显示整个轨迹
          if (points.length > 1) {
            const bounds = new BMapGL.Bounds(
              new BMapGL.Point(
                Math.min(...validPoints.map(p => p.lng)),
                Math.min(...validPoints.map(p => p.lat))
              ),
              new BMapGL.Point(
                Math.max(...validPoints.map(p => p.lng)),
                Math.max(...validPoints.map(p => p.lat))
              )
            );
            this.map.setViewport(bounds);
          }
          
        } else {
          console.log('无轨迹数据');
        }
      } catch (error) {
        console.error('加载历史轨迹失败:', error);
      }
    },

    async checkCollisions() {
      try {
        this.collisionChecking = true;
        const response = await axios.get(`${this.apiBaseUrl}/api/collision-check`);
        const alerts = response.data;
        
        this.alertCount = alerts.length;
        this.highRiskCount = alerts.filter(a => a.severity === 'high').length;
        this.mediumRiskCount = alerts.filter(a => a.severity === 'medium').length;

        const resultsHtml = alerts.length === 0 ? 
          '<div style="background:#f6ffed;border:1px solid #b7eb8f;padding:10px;border-radius:4px">✅ 当前无碰撞风险</div>' :
          alerts.map(alert => `
            <div style="background:#fff2f0;border:1px solid #ffccc7;padding:10px;margin:5px 0;border-radius:4px">
              <h4 style="color:#ff4d4f">⚠️ 碰撞风险警告!</h4>
              <p>无人机 ${alert.drone_a} 和 ${alert.drone_b}</p>
              <p>当前距离: ${alert.current_distance.toFixed(2)} 米</p>
              <p>预计碰撞时间: ${alert.time_to_collision.toFixed(1)} 秒后</p>
              <p>风险等级: ${alert.severity === 'high' ? '高' : '中'}</p>
            </div>
          `).join('');

        this.$refs.collisionResults.innerHTML = resultsHtml;
      } catch (error) {
        console.error('碰撞检测失败:', error);
        this.$refs.collisionResults.innerHTML = 
          '<div style="background:#fff2f0;border:1px solid #ffccc7;padding:10px;border-radius:4px">❌ 检测失败，请重试</div>';
      } finally {
        this.collisionChecking = false;
      }
    },

    async handleSearch() {
      if (this.searchTimeout) {
        clearTimeout(this.searchTimeout);
      }
      
      this.searchTimeout = setTimeout(async () => {
        const searchTerms = this.searchQuery.split(',').map(term => term.trim()).filter(term => term);
        
        if (searchTerms.length === 0) {
          this.searchResults = [];
          return;
        }
        
        try {
          const response = await axios.get(`${this.apiBaseUrl}/api/db/drones/current`);
          const drones = response.data;
          
          this.searchResults = drones.filter(drone => 
            searchTerms.some(term => 
              drone.serial && drone.serial.toLowerCase().includes(term.toLowerCase())
            )
          );
        } catch (error) {
          console.error('搜索失败:', error);
          this.searchResults = [];
        }
      }, 300);
    },

    async focusOnDrone(drone) {
      try {
        if (!drone || !drone.lat || !drone.lng) {
          console.error('无效的无人机数据');
          return;
        }

        const point = new BMapGL.Point(drone.lng, drone.lat);
        
        // 清理现有状态
        if (this.currentInfoWindow) {
          this.map.closeInfoWindow();
          this.currentInfoWindow = null;
        }

        if (this.historyPolyline) {
          this.map.removeOverlay(this.historyPolyline);
          this.historyPolyline = null;
        }

        // 更新地图视图
        this.map.centerAndZoom(point, 15);
        await this.showDroneInfo(drone, point);
        
      } catch (error) {
        console.error('聚焦无人机失败:', error);
      }
    },

    async showDroneInfo(drone, point) {
      try {
        // 如果已经有打开的信息窗口，先关闭它
        if (this.currentInfoWindow) {
          this.map.closeInfoWindow();
        }

        // 显示历史轨迹
        await this.showserialhistory(drone.serial);

        // 计算速度
        const verticalSpeed = drone.vz || 0;
        const horizontalSpeed = Math.sqrt((drone.vx || 0)**2 + (drone.vy || 0)**2);
        
        const content = `
          <div class="drone-info">
            <p><strong>基本信息</strong></p>
            <p>序列号: ${drone.serial}</p>
            <p>当前位置: ${drone.lat.toFixed(6)}°N, ${drone.lng.toFixed(6)}°E</p>
            <p>高度: ${drone.z || 0} 米</p>
            
            <p><strong>速度信息</strong></p>
            <p>水平速度: ${horizontalSpeed.toFixed(2)} m/s</p>
            <p>垂直速度: ${verticalSpeed.toFixed(2)} m/s</p>
            <p>航向: ${drone.direction || 0}°</p>
            
            <p><strong>飞行员位置</strong></p>
            <p>坐标: ${drone.pilot_lat?.toFixed(6) || 0}°N, ${drone.pilot_lng?.toFixed(6) || 0}°E</p>
            
            <p><strong>时间信息</strong></p>
            <p>最后更新: ${new Date(drone.last_updated).toLocaleString()}</p>
          </div>
        `;

        const infoWindow = new BMapGL.InfoWindow(content, {
          width: '100%',
          height: '100%',
          title: "无人机详细信息",
          enableAutoPan: true,
          enableCloseOnClick: true
        });
        
        // 为信息窗口添加关闭事件监听
        infoWindow.addEventListener('close', () => {
          this.currentInfoWindow = null;
        });
        
        // 保存当前信息窗口引用并显示
        this.currentInfoWindow = infoWindow;
        this.map.openInfoWindow(infoWindow, point);
      } catch (error) {
        console.error('显示无人机信息失败:', error);
      }
    },

    viewDroneList() {
      // 保存当前状态
      sessionStorage.setItem('mapState', JSON.stringify({
        center: this.map.getCenter(),
        zoom: this.map.getZoom(),
        tilt: this.map.getTilt()
      }));
      this.$router.push('/drones');
    },

    viewLogs() {
      this.$router.push('/logs');
    },

    restoreMapState() {
      // 恢复之前的地图状态
      const savedState = sessionStorage.getItem('mapState');
      if (savedState) {
        const state = JSON.parse(savedState);
        this.map.centerAndZoom(new BMapGL.Point(state.center.lng, state.center.lat), state.zoom);
        this.map.setTilt(state.tilt);
        sessionStorage.removeItem('mapState'); // 清除保存的状态
      }
    }
  },

  // 添加路由守卫
  beforeRouteEnter(to, from, next) {
    next(vm => {
      if (from.path === '/drones') {
        vm.$nextTick(() => {
          vm.restoreMapState();
        });
      }
    });
  }
}
</script>

<style scoped>
.map-container {
  position: relative;
  width: 100%;
  height: 100%;
}

#map-container {
  width: 100%;
  height: 100%;
}

.control-panel {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 1000;
}

.collision-check-btn {
  background-color: #ff0000;
  color: #ffffff;
  border: none;
  padding: 5px 10px;
  cursor: pointer;
}

.search-panel {
  position: fixed;
  left: 20px;
  bottom: 20px;
  background: transparent;
  padding: 15px;
  z-index: 1001;
  width: 300px;
}

.search-input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  margin-bottom: 10px;
}

.search-results {
  max-height: 400px;
  overflow-y: auto;
  background: transparent;
}

.search-item {
  background: rgba(255, 255, 255, 0.95);
  padding: 15px;
  margin: 5px 0;
  border-radius: 4px;
  transition: all 0.3s ease;
  cursor: pointer;
}

.search-item:hover {
  background: #e6f7ff;
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.collision-panel {
  background: white;
  padding: 15px;
  border-radius: 4px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.3);
  min-width: 250px;
}

.collision-summary {
  margin-bottom: 15px;
  padding: 10px;
  background: #f5f5f5;
  border-radius: 4px;
}

.collision-summary h3 {
  margin: 0 0 10px 0;
  color: #1890ff;
}

.collision-summary p {
  margin: 5px 0;
  color: #333;
}

.collision-results {
  max-height: 300px;
  overflow-y: auto;
  margin-top: 10px;
}

.view-list-btn {
  position: fixed;
  left: 20px;
  top: 20px;
  z-index: 1001;
}

.list-btn {
  background: #1890ff;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
  transition: all 0.3s;
}

.list-btn:hover {
  background: #40a9ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.view-logs-btn {
  position: fixed;
  left: 20px;
  top: 80px;
  z-index: 1001;
}

.logs-btn {
  background: #1890ff;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
  transition: all 0.3s;
}

.logs-btn:hover {
  background: #40a9ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
</style>