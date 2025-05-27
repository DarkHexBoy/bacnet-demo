import time
import threading
import configparser
import os
from bacpypes.app import BIPSimpleApplication
from bacpypes.local.device import LocalDeviceObject
from bacpypes.object import AnalogValueObject
from bacpypes.core import run, stop

# 读取配置文件 run.ini（适配 PyInstaller，优先用当前工作目录）
config = configparser.ConfigParser()
ini_path = os.path.join(os.getcwd(), 'run.ini')
config.read(ini_path, encoding='utf-8')

bacnet_cfg = config['bacnet']
if 'ip' not in bacnet_cfg:
    raise RuntimeError('配置文件 run.ini 缺少 [bacnet] 部分的 ip 参数，程序退出。')
ip = bacnet_cfg['ip']
mask = bacnet_cfg.get('mask', '24')
port = bacnet_cfg.get('port', '47809')
device_name = bacnet_cfg.get('objectName', 'Lockon BACnet Develop Server')
device_id = int(bacnet_cfg.get('objectIdentifier', '12345'))

# 1. 创建设备对象
this_device = LocalDeviceObject(
    objectName=device_name,
    objectIdentifier=device_id,
    maxApduLengthAccepted=1024,
    segmentationSupported="segmentedBoth",
    vendorIdentifier=15,
)

# 2. 创建BACnet/IP应用，绑定本地IP和端口（从配置读取）
this_application = BIPSimpleApplication(this_device, f"{ip}/{mask}:{port}")

# 3. 创建模拟传感器对象
analog1 = AnalogValueObject(
    objectIdentifier=('analogValue', 1),
    objectName="Temperature Sensor",
    presentValue=23.5,
    units=62,  # degreesCelsius
    statusFlags=[0, 0, 0, 0],
)
analog1.covIncrement = 0.1

analog2 = AnalogValueObject(
    objectIdentifier=('analogValue', 2),
    objectName="Humidity Sensor",
    presentValue=56.7,
    units=57,  # percentRelativeHumidity
    statusFlags=[0, 0, 0, 0],
)
analog2.covIncrement = 0.2

analog3 = AnalogValueObject(
    objectIdentifier=('analogValue', 3),
    objectName="Pressure Sensor",
    presentValue=101.3,
    units=97,  # hectopascals
    statusFlags=[0, 0, 0, 0],
)
analog3.covIncrement = 0.3

# 4. 添加对象到应用
this_application.add_object(analog1)
this_application.add_object(analog2)
this_application.add_object(analog3)

print(f"BACnet/IP Server started on {ip}:{port}")

# 5. 动态更新传感器值的线程函数
def update_sensors():
    while True:
        # 简单地对数值做点变化，模拟传感器数据波动
        analog1.presentValue += 0.1
        if analog1.presentValue > 30:
            analog1.presentValue = 23.5

        analog2.presentValue += 0.2
        if analog2.presentValue > 70:
            analog2.presentValue = 56.7

        analog3.presentValue += 0.3
        if analog3.presentValue > 105:
            analog3.presentValue = 101.3

        time.sleep(5)  # 每5秒更新一次

# 6. 启动更新线程（守护线程，程序退出自动结束）
update_thread = threading.Thread(target=update_sensors, daemon=True)
update_thread.start()

# 7. 启动 BACnet 服务事件循环
run()
