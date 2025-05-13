import { createRouter, createWebHistory } from 'vue-router'
import MapView from '../components/MapView.vue'
import DroneList from '../components/DroneList.vue'
import LogView from '../components/LogView.vue'
import DroneHistory from '../components/DroneHistory.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: MapView
  },
  {
    path: '/logs',
    name: 'logs',
    component: LogView
  },
  {
    path: '/drones',
    name: 'drones',
    component: DroneList
  },
  {
    path: '/drone/:serial/history',
    name: 'DroneHistory',
    component: DroneHistory
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router