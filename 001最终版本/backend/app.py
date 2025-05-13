from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS
import mysql.connector
from datetime import datetime
import json
from collision_detection import check_collision_risk
import os

app = Flask(__name__, 
    static_folder='../frontend',  
    static_url_path=''
)
CORS(app)

# 数据库配置
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'lm1596377283',
    'database': 'aircraft_data_db'
}

def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        print(f"数据库连接错误: {err}")
        raise

@app.route('/api/db/drones')
def get_drones():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 只查询基本信息表
        cursor.execute("SELECT * FROM drones ORDER BY drone_id")
        
        drones = cursor.fetchall()
        
        # 转换飞行员坐标格式
        for drone in drones:
            if 'pilot_lat' in drone:
                drone['pilot_lat'] = float(drone['pilot_lat']) / 10000000
            if 'pilot_lng' in drone:
                drone['pilot_lng'] = float(drone['pilot_lng']) / 10000000
        
        cursor.close()
        conn.close()
        
        return jsonify(drones)
    except mysql.connector.Error as e:
        print(f"数据库查询错误: {e}")
        return jsonify({"error": f"数据库错误: {str(e)}"}), 500
    except Exception as e:
        print(f"未知错误: {e}")
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500

@app.route('/api/db/drones/current')
def get_drones_current():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT d.serial, d.direction, d.ew_dir, d.pilot_lat, d.pilot_lng, z,
                   c.lat, c.lng, c.vx, c.vy, c.vz, c.last_updated
            FROM drones d
            LEFT JOIN drone_current_info c ON d.drone_id = c.drone_id
            ORDER BY c.last_updated DESC
        """)
        
        drones = cursor.fetchall()
        
        # 转换所有坐标格式
        for drone in drones:
            if 'lat' in drone and drone['lat']:
                drone['lat'] = float(drone['lat']) / 10000000
            if 'lng' in drone and drone['lng']:
                drone['lng'] = float(drone['lng']) / 10000000
            if 'z' in drone and drone['z']:
                drone['z'] = float(drone['z'])
            if 'pilot_lat' in drone and drone['pilot_lat']:
                drone['pilot_lat'] = float(drone['pilot_lat']) / 10000000
            if 'pilot_lng' in drone and drone['pilot_lng']:
                drone['pilot_lng'] = float(drone['pilot_lng']) / 10000000
        
        cursor.close()
        conn.close()
        
        return jsonify(drones)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drone/<serial>/trajectory', methods=['GET'])
def get_drone_trajectory(serial):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        print(f"开始查询无人机 {serial} 的轨迹数据") # 添加调试日志
        
        # 先获取drone_id
        cursor.execute("SELECT drone_id FROM drones WHERE serial = %s", (serial,))
        result = cursor.fetchone()
        if not result:
            print(f"未找到无人机: {serial}")  # 添加调试日志
            return jsonify({'error': 'Drone not found'}), 404
        
        drone_id = result['drone_id']
        print(f"找到无人机ID: {drone_id}")  # 添加调试日志
        
        # 修改SQL查询以确保数据完整性和性能
        cursor.execute("""
            SELECT 
                d.serial,
                h.lat,
                h.lng,
                h.z,
                h.vx,
                h.vy,
                h.vz,
                h.timestamp 
            FROM drone_historical_tracks h
            JOIN drones d ON h.drone_id = d.drone_id
            WHERE h.drone_id = %s 
            AND h.timestamp >= NOW() - INTERVAL 30 MINUTE  -- 减少时间范围到30分钟
            AND h.lat IS NOT NULL                         -- 确保坐标数据存在
            AND h.lng IS NOT NULL
            ORDER BY h.timestamp ASC                      -- 按时间升序排序
            LIMIT 1000                                    -- 限制返回记录数
        """, (drone_id,))
        
        trajectory = cursor.fetchall()
        print(f"查询到 {len(trajectory)} 条轨迹记录")  # 添加调试日志
        
        # 转换坐标格式和时间戳
        formatted_trajectory = []
        for point in trajectory:
            try:
                formatted_point = {
                    'lat': float(point['lat']) / 10000000,
                    'lng': float(point['lng']) / 10000000,
                    'z': float(point['z']) if point['z'] else 0,
                    'vx': float(point['vx']) if point['vx'] else 0,
                    'vy': float(point['vy']) if point['vy'] else 0,
                    'vz': float(point['vz']) if point['vz'] else 0,
                    'timestamp': point['timestamp'].isoformat()
                }
                formatted_trajectory.append(formatted_point)
            except (ValueError, TypeError) as e:
                print(f"数据转换错误: {e}, 原始数据: {point}")  # 添加调试日志
                continue
        
        cursor.close()
        conn.close()
        
        return jsonify(formatted_trajectory)
        
    except Exception as e:
        print(f"获取轨迹数据失败: {str(e)}")  # 添加错误日志
        return jsonify({'error': str(e)}), 500

@app.route('/api/collision-alerts', methods=['GET'])
def get_collision_alerts():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 获取所有无人机当前位置
        cursor.execute("""
            SELECT d.serial, c.* 
            FROM drone_current_info c
            JOIN drones d ON c.drone_id = d.drone_id
        """)
        
        drones = cursor.fetchall()
        
        # 检查碰撞风险
        alerts = check_collision_risk(drones)
        
        cursor.close()
        conn.close()
        
        return jsonify(alerts)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 添加日志目录配置
LOG_DIR = os.path.join(os.path.dirname(__file__), 'collision_logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
    
@app.route('/api/logs/list', methods=['GET'])
def list_logs():
    """获取所有日志文件列表"""
    try:
        print(f"正在读取日志目录: {LOG_DIR}")  # 调试信息
        logs = []
        files = os.listdir(LOG_DIR)
        print(f"发现文件: {files}")  # 调试信息
        
        for file in sorted(files, reverse=True):
            if file.startswith('collision_alert_') and file.endswith('.log'):
                file_path = os.path.join(LOG_DIR, file)
                file_stat = os.stat(file_path)
                
                try:
                    # 确保正确提取文件名中的时间戳部分
                    date_str = file.replace('collision_alert_', '').replace('.log', '')
                    if len(date_str) != 15:  # 检查时间戳长度是否正确
                        print(f"跳过格式错误的文件名: {file}")
                        continue
                        
                    timestamp = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                    
                    log_info = {
                        'filename': file,
                        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        'size': file_stat.st_size,
                        'created_at': datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    print(f"处理日志: {log_info}")  # 调试信息
                    logs.append(log_info)
                    
                except Exception as e:
                    print(f"处理日志文件 {file} 时出错: {str(e)}")
                    continue
        
        print(f"返回日志列表: {logs}")  # 调试信息
        return jsonify(logs)
        
    except Exception as e:
        print(f"获取日志列表失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/<filename>', methods=['GET'])
def get_log_content(filename):
    """获取指定日志文件的内容"""
    try:
        # 安全检查：确保文件名合法
        if not filename.startswith('collision_alert_') or not filename.endswith('.log'):
            return jsonify({'error': 'Invalid filename'}), 400
            
        file_path = os.path.join(LOG_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'Log file not found'}), 404
            
        # 检查文件是否在LOG_DIR目录下
        if not os.path.abspath(file_path).startswith(os.path.abspath(LOG_DIR)):
            return jsonify({'error': 'Access denied'}), 403
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修复: 正确提取时间戳部分
        date_str = filename.replace('collision_alert_', '').replace('.log', '')
        if len(date_str) != 15:  # 确保时间戳长度正确
            raise ValueError(f"Invalid timestamp format in filename: {filename}")
            
        timestamp = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
            
        return jsonify({
            'filename': filename,
            'content': content,
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        print(f"获取日志内容失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/collision-check', methods=['GET'])
def check_collisions():
    """检查当前所有无人机的碰撞风险"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT d.serial, c.*
            FROM drone_current_info c 
            JOIN drones d ON c.drone_id = d.drone_id
        """)
        drones = cursor.fetchall()
        
        # 检查碰撞风险
        alerts = check_collision_risk(drones)
        
        # 记录日志
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(LOG_DIR, f'collision_alert_{timestamp}.log')
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"碰撞风险检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"检测到 {len(alerts)} 个潜在碰撞风险\n\n")
            
            if alerts:
                for alert in alerts:
                    f.write("=" * 50 + "\n")
                    f.write(f"风险等级: {alert['severity']}\n")
                    f.write(f"预计碰撞时间: {alert['time_to_collision']:.2f} 秒后\n")
                    f.write(f"当前距离: {alert['current_distance']:.2f} 米\n\n")
                    
                    # 记录无人机A的信息
                    drone_a = next(d for d in drones if d['serial'] == alert['drone_a'])
                    f.write("无人机A信息:\n")
                    f.write(f"序列号: {drone_a['serial']}\n")
                    f.write(f"位置: {drone_a['lat']/10000000:.6f}°N, {drone_a['lng']/10000000:.6f}°E\n")
                    f.write(f"高度: {drone_a['z']} 米\n")
                    f.write(f"速度: vx={drone_a['vx']:.2f}, vy={drone_a['vy']:.2f}, vz={drone_a['vz']:.2f}\n\n")
                    
                    # 记录无人机B的信息
                    drone_b = next(d for d in drones if d['serial'] == alert['drone_b'])
                    f.write("无人机B信息:\n")
                    f.write(f"序列号: {drone_b['serial']}\n")
                    f.write(f"位置: {drone_b['lat']/10000000:.6f}°N, {drone_b['lng']/10000000:.6f}°E\n")
                    f.write(f"高度: {drone_b['z']} 米\n")
                    f.write(f"速度: vx={drone_b['vx']:.2f}, vy={drone_b['vy']:.2f}, vz={drone_b['vz']:.2f}\n\n")
            else:
                f.write("本次检测未发现碰撞风险。\n")
        
        cursor.close()
        conn.close()
        
        # 返回结果时包含日志文件名
        return jsonify(alerts)
        
    except Exception as e:
        print(f"碰撞检测失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)