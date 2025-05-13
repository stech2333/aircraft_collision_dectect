import math
import numpy as np
import imp
import os
import glob

# 全局变量初始化
USE_NBLIST = False
nblist = None

def init_nblist():
    """初始化nblist库"""
    global USE_NBLIST, nblist
    
    try:
        # 查找当前目录下的.so文件
        so_files = glob.glob('nblist*.so')
        if not so_files:
            # 查找上级目录
            so_files = glob.glob('../nblist*.so')
            if not so_files:
                # 查找dpnblist构建目录
                so_files = glob.glob('../../dpnblist/build/nblist*.so')
        
        if so_files:
            so_path = so_files[0]
            nblist = imp.load_dynamic('nblist', so_path)
            USE_NBLIST = True
            print(f"成功加载nblist库: {so_path}")
        else:
            print("找不到nblist*.so文件")
            
    except Exception as e:
        print(f"无法加载nblist库,将使用传统方法: {e}")
        USE_NBLIST = False

# 初始化nblist
init_nblist()

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    使用Haversine公式计算两点间的大圆距离(米)
    输入参数为度数格式的经纬度
    """
    R = 6371008.8  # 地球平均半径(米)
    
    # 转换为弧度
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine公式
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # 使用半正矢公式
    a = math.sin(dlat/2)**2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    distance = R * c
    return distance

def get_xy_from_latlon(lat: float, lon: float, ref_lat: float, ref_lon: float) -> tuple[float, float]:
    """
    将经纬度转换为相对于参考点的平面坐标(米)
    使用局部切平面投影
    """
    # 计算南北方向距离
    y = haversine_distance(ref_lat, ref_lon, lat, ref_lon)
    if lat < ref_lat:
        y = -y
        
    # 计算东西方向距离
    x = haversine_distance(ref_lat, ref_lon, ref_lat, lon)
    if lon < ref_lon:
        x = -x
    
    # 打印调试信息
    #print(f"坐标转换: ({lat}, {lon}) -> ({x}, {y})")
    #print(f"参考点: ({ref_lat}, {ref_lon})")
    #print(f"距离: 南北={abs(y)}米, 东西={abs(x)}米")
        
    return x, y

class Drone:
    """无人机数据结构"""
    def __init__(self, x0=0, y0=0, z0=0, vx=0, vy=0, vz=0):
        self.x0 = x0  # 初始位置坐标(米)
        self.y0 = y0
        self.z0 = z0
        self.vx = vx  # 速度向量(米/秒)
        self.vy = vy
        self.vz = vz

def detect_collision(a: Drone, b: Drone) -> tuple[bool, float]:
    """
    碰撞检测函数
    返回: (是否会碰撞, 碰撞时间)
    """
    # 定义常量
    R = 1.0        # 无人机半径(米)
    EPSILON = 1e-6  # 浮点数精度

    # 1. 计算相对位置和相对速度(A相对于B)
    dx0 = a.x0 - b.x0
    dy0 = a.y0 - b.y0
    dz0 = a.z0 - b.z0

    dvx = a.vx - b.vx
    dvy = a.vy - b.vy
    dvz = a.vz - b.vz

    # 2. 计算二次方程系数
    a_coef = dvx * dvx + dvy * dvy + dvz * dvz
    b_coef = dx0 * dvx + dy0 * dvy + dz0 * dvz
    c_coef = dx0 * dx0 + dy0 * dy0 + dz0 * dz0 - 4.0 * R * R

    # 3. 判断是否相对静止
    if abs(a_coef) < EPSILON:
        if c_coef <= 0:
            return True, 0.0  # 已经发生碰撞
        return False, float('inf')  # 永远不会碰撞

    # 4. 计算判别式
    discriminant = b_coef * b_coef - a_coef * c_coef

    # 5. 判定是否有实数解
    if discriminant < -EPSILON:
        return False, float('inf')  # 无实数解,不会发生碰撞

    # 6. 计算碰撞时间
    sqrt_discriminant = math.sqrt(max(discriminant, 0.0))
    t1 = (-b_coef - sqrt_discriminant) / a_coef
    t2 = (-b_coef + sqrt_discriminant) / a_coef

    # 7. 选择有效的碰撞时间
    t = float('inf')

    if t1 >= -EPSILON:
        t = t1
    if t2 >= -EPSILON and t2 < t:
        t = t2

    if t == float('inf'):
        return False, float('inf')  # 碰撞发生在过去
    return True, t  # 将在未来发生碰撞

def check_collision_risk(drones_data: list) -> list:
    """
    检查所有无人机之间的碰撞风险
    """
    global USE_NBLIST, nblist
    alerts = []
    # 使用集合存储已检查过的无人机对
    checked_pairs = set()
    print(f"开始检测碰撞风险,无人机数量: {len(drones_data)}")
    
    if not drones_data or len(drones_data) < 2:
        return alerts
        
    # 使用第一个无人机的位置作为参考点
    ref_lat = drones_data[0].get('lat', 0) / 10000000 if drones_data[0].get('lat') else 0
    ref_lon = drones_data[0].get('lng', 0) / 10000000 if drones_data[0].get('lng') else 0
    
    # 准备无人机位置数据
    positions = []
    drones = []
    
    for data in drones_data:
        # 确保经纬度值正确转换
        lat = float(data.get('lat', 0)) / 10000000 if data.get('lat') else 0
        lon = float(data.get('lng', 0)) / 10000000 if data.get('lng') else 0
        
        x0, y0 = get_xy_from_latlon(lat, lon, ref_lat, ref_lon)
        z0 = float(data.get('z', 0))
        
        # 打印每个无人机的位置信息
        print(f"无人机 {data['serial']}:")
        print(f"- 经纬度: ({lat}, {lon})")
        print(f"- 平面坐标: ({x0}, {y0})")
        print(f"- 高度: {z0}")
        
        positions.append([x0, y0, z0])
        
        drone = Drone(
            x0=x0, 
            y0=y0,
            z0=z0,
            vx=data.get('vx', 0),
            vy=data.get('vy', 0),
            vz=data.get('vz', 0)
        )
        drones.append((data['serial'], drone))
    
    def calculate_collision_point(drone_a: Drone, drone_b: Drone, t: float) -> tuple:
        """计算碰撞点坐标"""
        x = drone_a.x0 + drone_a.vx * t
        y = drone_a.y0 + drone_a.vy * t
        z = drone_a.z0 + drone_a.vz * t
        return (x, y, z)
    
    def calculate_current_distance(drone_a: Drone, drone_b: Drone) -> float:
        """计算当前距离"""
        dx = drone_a.x0 - drone_b.x0
        dy = drone_a.y0 - drone_b.y0
        dz = drone_a.z0 - drone_b.z0
        return math.sqrt(dx*dx + dy*dy + dz*dz)

    def get_latlon_from_xy(x: float, y: float, ref_lat: float, ref_lon: float) -> tuple[float, float]:
        """将平面坐标转换回经纬度"""
        # 计算纬度变化
        dlat = y / 111111  # 每度纬度约111.111公里
        new_lat = ref_lat + dlat
        
        # 计算经度变化
        dlon = x / (111111 * math.cos(math.radians(ref_lat)))
        new_lon = ref_lon + dlon
        
        return new_lat, new_lon

    # 使用nblist算法或传统方法
    if USE_NBLIST:
        try:
            positions = np.array(positions)
            nblist.set_num_threads(4)
            
            max_coords = np.max(positions, axis=0)
            min_coords = np.min(positions, axis=0)
            domain_size = np.ceil(max_coords - min_coords).tolist()
            domain_size = [max(2000, d) for d in domain_size]
            
            box = nblist.Box(domain_size, [90.0, 90.0, 90.0])
            nb = nblist.NeighborList("Octree-CPU")
            nb.build(box, positions, 1000.0)
            pairs = nb.get_neighbor_pair()
            
            for i, j in pairs:
                serial_a, drone_a = drones[i]
                serial_b, drone_b = drones[j]
                
                # 跳过已检查过的对
                pair_key = tuple(sorted([serial_a, serial_b]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)
                
                will_collide, collision_time = detect_collision(drone_a, drone_b)
                if will_collide and collision_time < 60:
                    current_distance = calculate_current_distance(drone_a, drone_b)
                    collision_point = calculate_collision_point(drone_a, drone_b, collision_time)
                    
                    # 获取两个无人机的当前经纬度
                    drone_a_lat, drone_a_lng = get_latlon_from_xy(drone_a.x0, drone_a.y0, ref_lat, ref_lon)
                    drone_b_lat, drone_b_lng = get_latlon_from_xy(drone_b.x0, drone_b.y0, ref_lat, ref_lon)
                    
                    alert = {
                        'drone_a': serial_a,
                        'drone_b': serial_b,
                        'time_to_collision': collision_time,
                        'current_distance': current_distance,
                        'collision_point': {
                            'x': collision_point[0],
                            'y': collision_point[1],
                            'z': collision_point[2]
                        },
                        'severity': 'high' if collision_time < 5 else 'medium',
                        'drone_a_lat': drone_a_lat,
                        'drone_a_lng': drone_a_lng,
                        
                        'drone_b_lat': drone_b_lat,
                        'drone_b_lng': drone_b_lng
                    }
                    alerts.append(alert)
                    print(f"检测到碰撞风险: {alert}")
                    
        except Exception as e:
            print(f"八叉树算法失败,使用传统方法: {e}")
            USE_NBLIST = False
    
    # 如果nblist不可用或失败,使用传统方法
    if not USE_NBLIST:
        for i in range(len(drones)):
            for j in range(i + 1, len(drones)):  # 只检查一半的组合
                serial_a, drone_a = drones[i]
                serial_b, drone_b = drones[j]
                
                # 跳过已检查过的对
                pair_key = tuple(sorted([serial_a, serial_b]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)
                
                will_collide, collision_time = detect_collision(drone_a, drone_b)
                if will_collide and collision_time < 60:
                    current_distance = calculate_current_distance(drone_a, drone_b)
                    collision_point = calculate_collision_point(drone_a, drone_b, collision_time)
                    
                    # 获取两个无人机的当前经纬度
                    drone_a_lat, drone_a_lng = get_latlon_from_xy(drone_a.x0, drone_a.y0, ref_lat, ref_lon)
                    drone_b_lat, drone_b_lng = get_latlon_from_xy(drone_b.x0, drone_b.y0, ref_lat, ref_lon)
                    
                    alert = {
                        'drone_a': serial_a,
                        'drone_b': serial_b,
                        'time_to_collision': collision_time,
                        'current_distance': current_distance,
                        'collision_point': {
                            'x': collision_point[0],
                            'y': collision_point[1],
                            'z': collision_point[2]
                        },
                        'severity': 'high' if collision_time < 30 else 'medium',
                        'drone_a_lat': drone_a_lat,
                        'drone_a_lng': drone_a_lng,
                        'drone_b_lat': drone_b_lat,
                        'drone_b_lng': drone_b_lng
                    }
                    alerts.append(alert)
                    print(f"检测到碰撞风险: {alert}")

    print(f"碰撞检测完成,发现{len(alerts)}个风险")
    return alerts