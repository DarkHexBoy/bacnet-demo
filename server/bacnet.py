import time
import threading
import configparser
import os
from bacpypes.app import BIPSimpleApplication
from bacpypes.local.device import LocalDeviceObject
from bacpypes.object import AnalogValueObject
from bacpypes.core import run, stop

def load_config():
    config = configparser.ConfigParser()
    ini_path = os.path.join(os.getcwd(), 'run.ini')
    config.read(ini_path, encoding='utf-8')
    bacnet_cfg = config['bacnet']
    if 'ip' not in bacnet_cfg:
        raise RuntimeError('配置文件 run.ini 缺少 [bacnet] 部分的 ip 参数，程序退出。')
    return {
        'ip': bacnet_cfg['ip'],
        'mask': bacnet_cfg.get('mask', '24'),
        'port': bacnet_cfg.get('port', '47809'),
        'objectName': bacnet_cfg.get('objectName', 'Lockon BACnet Develop Server'),
        'objectIdentifier': int(bacnet_cfg.get('objectIdentifier', '12345')),
    }

def create_device(config):
    return LocalDeviceObject(
        objectName=config['objectName'],
        objectIdentifier=config['objectIdentifier'],
        maxApduLengthAccepted=1024,
        segmentationSupported="segmentedBoth",
        vendorIdentifier=15,
    )

def create_application(device, config):
    address = f"{config['ip']}/{config['mask']}:{config['port']}"
    return BIPSimpleApplication(device, address)

# 需要考虑从 mqtt broker 读取配置
# 然后再继续同 mqtt broker 读取数据更新过来
def create_analog_objects():
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
    return [analog1, analog2, analog3]

def add_objects_to_app(app, objects):
    for obj in objects:
        app.add_object(obj)

def sensor_update_loop(analogs, stop_event):
    while not stop_event.is_set():
        analogs[0].presentValue += 0.1
        if analogs[0].presentValue > 30:
            analogs[0].presentValue = 23.5
        analogs[1].presentValue += 0.2
        if analogs[1].presentValue > 70:
            analogs[1].presentValue = 56.7
        analogs[2].presentValue += 0.3
        if analogs[2].presentValue > 105:
            analogs[2].presentValue = 101.3
        time.sleep(5)

def main():
    config = load_config()
    device = create_device(config)
    app = create_application(device, config)
    analogs = create_analog_objects()
    add_objects_to_app(app, analogs)
    print(f"BACnet/IP Server started on {config['ip']}:{config['port']}")
    stop_event = threading.Event()
    update_thread = threading.Thread(target=sensor_update_loop, args=(analogs, stop_event), daemon=True)
    update_thread.start()
    try:
        run()
    finally:
        stop_event.set()
        update_thread.join()

if __name__ == "__main__":
    main()
