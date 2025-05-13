from scapy.all import sniff, Dot11, Dot11EltVendorSpecific
import struct
import mysql.connector
from datetime import datetime

# 消息类型 0 的偏移值和长度（根据实际情况调整）
# 假设从 OUI 和长度字段之后开始
MSG_TYPE_0_OFFSET = 5
MSG_TYPE_0_LENGTH = 25

# 消息类型 1 的偏移值和长度（根据实际情况调整）
MSG_TYPE_1_OFFSET = MSG_TYPE_0_OFFSET + MSG_TYPE_0_LENGTH
MSG_TYPE_1_LENGTH = 52

# 消息类型 4 的偏移值和长度（根据实际情况调整）
MSG_TYPE_4_OFFSET = MSG_TYPE_1_OFFSET + MSG_TYPE_1_LENGTH + 5
MSG_TYPE_4_LENGTH = 24

# 连接到 MySQL 数据库
mydb = mysql.connector.connect(
    host="localhost",  # 主机地址，根据实际情况修改
    user="root",  # 用户名，根据实际情况修改
    password="lm1596377283"  # 密码，根据实际情况修改
)

# 创建数据库（如果不存在）
mycursor = mydb.cursor()
mycursor.execute("CREATE DATABASE IF NOT EXISTS aircraft_data_db")
mycursor.close()

# 连接到新创建的数据库
mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="lm1596377283",
    database="aircraft_data_db"
)
mycursor = mydb.cursor()

# 创建基本信息表

mycursor.execute('''
CREATE TABLE IF NOT EXISTS drones (
    drone_id INT AUTO_INCREMENT PRIMARY KEY,
    serial VARCHAR(255) UNIQUE,
    pilot_lat INT,
    pilot_lng INT,
    direction TINYINT,
    ew_dir TINYINT
) ENGINE=InnoDB;
''')

# 创建实时信息表
mycursor.execute('''
CREATE TABLE IF NOT EXISTS drone_current_info (
    drone_id INT PRIMARY KEY,
    lat INT,
    lng INT,
    z INT,
    vx FLOAT,
    vy FLOAT,
    vz FLOAT,
    last_updated DATETIME,
    FOREIGN KEY (drone_id) REFERENCES drones(drone_id)
) ENGINE=InnoDB;
''')

# 创建历史轨迹表
mycursor.execute('''
CREATE TABLE IF NOT EXISTS drone_historical_tracks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    drone_id INT,
    lat INT,
    lng INT,
    z INT,
    vx FLOAT,
    vy FLOAT,
    vz FLOAT,
    timestamp DATETIME,
    FOREIGN KEY (drone_id) REFERENCES drones(drone_id),
    INDEX idx_drone_time (drone_id, timestamp)
) ENGINE=InnoDB;
''')
mydb.commit()


def packet_handler(packet):
    if packet.haslayer(Dot11) and packet.haslayer(Dot11EltVendorSpecific):
        vendor_specific = packet.getlayer(Dot11EltVendorSpecific)
        if vendor_specific.oui == 0xfa0bbc:
            vendor_info = vendor_specific.info

            # 解析消息类型 0
            msg_type_0 = vendor_info[MSG_TYPE_0_OFFSET:MSG_TYPE_0_OFFSET + MSG_TYPE_0_LENGTH]
            serial = msg_type_0[5:25].decode('utf-8')

            parsed_data = {
               'serial': serial,
                'direction': None,
                'ew_dir': None,
                'lat': None,
                'lng': None,
                'z': None,
                'vx': None,
                'vy': None,
                'vz': None,
                'timestamp': None,
                'pilot_lat': None,
                'pilot_lng': None
            }

            # 解析消息类型 1 与类型 4
            msg_type_1 = vendor_info[MSG_TYPE_1_OFFSET:MSG_TYPE_1_OFFSET + MSG_TYPE_1_LENGTH + MSG_TYPE_4_LENGTH]

            try:
                # 解析方向和 E/W 方向段位
                direction, ew_dir = struct.unpack("<BB", msg_type_1[4:6])
                # 解析纬度
                lat = struct.unpack("<i", msg_type_1[8:12])[0]
                # 解析经度
                lng = struct.unpack("<i", msg_type_1[12:16])[0]
                # 解析高度
                z = struct.unpack("<i", msg_type_1[16:20])[0]
                # 解析 x 方向速度
                vx = struct.unpack("<f", msg_type_1[20:24])[0]
                # 解析 y 方向速度
                vy = struct.unpack("<f", msg_type_1[24:28])[0]
                # 解析 z 方向速度
                vz = struct.unpack("<f", msg_type_1[28:32])[0]
                # 解析时间戳（十分之一秒）
                tenth_seconds = struct.unpack("<H", msg_type_1[40:42])[0]
                # 将十分之一秒转换为datetime
                minutes = tenth_seconds // 600
                seconds = (tenth_seconds % 600) / 10
                now = datetime.now()
                timestamp = datetime(now.year, now.month, now.day, now.hour, minutes, int(seconds))
                
                pilot_lat = struct.unpack("<i", msg_type_1[46:50])[0]
                pilot_lng = struct.unpack("<i", msg_type_1[50:54])[0]
                
                parsed_data['direction'] = direction
                parsed_data['ew_dir'] = ew_dir
                parsed_data['lat'] = lat
                parsed_data['lng'] = lng
                parsed_data['z'] = z
                parsed_data['vx'] = vx
                parsed_data['vy'] = vy
                parsed_data['vz'] = vz
                parsed_data['timestamp'] = timestamp
                parsed_data['pilot_lat'] = pilot_lat
                parsed_data['pilot_lng'] = pilot_lng

                # 1. 更新或插入基本信息表
                mycursor.execute("""
                    INSERT INTO drones (serial, pilot_lat, pilot_lng, direction, ew_dir) 
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                    pilot_lat = VALUES(pilot_lat),
                    pilot_lng = VALUES(pilot_lng),
                    direction = VALUES(direction),
                    ew_dir = VALUES(ew_dir)
                """, (serial, pilot_lat, pilot_lng, direction, ew_dir))
                
                # 获取drone_id
                if mycursor.lastrowid:
                    drone_id = mycursor.lastrowid
                else:
                    mycursor.execute("SELECT drone_id FROM drones WHERE serial = %s", (serial,))
                    drone_id = mycursor.fetchone()[0]

                # 2. 更新实时信息表
                mycursor.execute("""
                    INSERT INTO drone_current_info 
                    (drone_id, lat, lng, z, vx, vy, vz, last_updated)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                    lat = VALUES(lat),
                    lng = VALUES(lng),
                    z = VALUES(z),
                    vx = VALUES(vx),
                    vy = VALUES(vy),
                    vz = VALUES(vz),
                    last_updated = VALUES(last_updated)
                """, (drone_id, lat, lng, z, vx, vy, vz, timestamp))

                # 3. 插入历史轨迹
                mycursor.execute("""
                    INSERT INTO drone_historical_tracks 
                    (drone_id, lat, lng, z, vx, vy, vz, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (drone_id, lat, lng, z, vx, vy, vz, timestamp))

                mydb.commit()
                print(f"成功更新无人机 {serial} 的信息")

            except struct.error as e:
                print(f"解析消息类型 1 时出错: {e}")
            except mysql.connector.Error as e:
                print(f"数据库操作错误: {e}")
                mydb.rollback()
    return None


def start_sniffing(interface):
    def collect_results(packet):
        packet_handler(packet)
    try:
        sniff(iface=interface, prn=collect_results)
    except KeyboardInterrupt:
        print("嗅探过程被中断，停止监听。")


# 开始嗅探
interface = input("请输入要监听的网络接口名称（例如 wlan1）：")
start_sniffing(interface)

# 关闭数据库连接
mycursor.close()
mydb.close()