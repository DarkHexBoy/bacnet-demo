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

def load_device_ini():
    config_parser = configparser.ConfigParser()
    ini_path = os.path.join(os.getcwd(), 'device.ini')
    config_parser.read(ini_path, encoding='utf-8')
    return config_parser

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
def create_analog_objects(config_parser):
    analogs = []
    for section in config_parser.sections():
        if section.startswith('analogValue'):
            cfg = config_parser[section]
            kwargs = {
                'objectIdentifier': ('analogValue', int(cfg.get('objectIdentifier', '1'))),
                'objectName': cfg.get('objectName', f'AnalogValue{section[-1]}'),
                'presentValue': float(cfg.get('presentValue', '0')),
                'units': int(cfg.get('units', '62')),
                'statusFlags': [int(x) for x in cfg.get('statusFlags', '0,0,0,0').split(',')],
                'description': cfg.get('description', ''),
                'outOfService': cfg.getboolean('outOfService', False),
                'eventState': cfg.get('eventState', 'normal'),
                'reliability': cfg.get('reliability', 'no-fault-detected'),
                'minPresValue': float(cfg.get('minPresValue', '-1000000')),
                'maxPresValue': float(cfg.get('maxPresValue', '1000000')),
                'resolution': float(cfg.get('resolution', '0.01')),
            }
            analog = AnalogValueObject(**kwargs)
            analog.covIncrement = float(cfg.get('covIncrement', '0.1'))
            analogs.append(analog)
    return analogs

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

def input_listener():
    while True:
        cmd = input()
        if cmd.strip().lower() in ("quit", "exit"):
            print("收到退出指令，正在关闭 BACnet 服务...")
            stop()
            break

def main():
    config = load_config()
    device_ini = load_device_ini()
    device = create_device(config)
    app = create_application(device, config)
    analogs = create_analog_objects(device_ini)
    if not analogs:
        raise RuntimeError('配置文件 device.ini 未配置任何 [analogValueX] 点位，程序退出。')
    add_objects_to_app(app, analogs)
    print(f"BACnet/IP Server started on {config['ip']}:{config['port']}")
    print("输入 quit 或 exit 可安全退出服务...")
    stop_event = threading.Event()
    update_thread = threading.Thread(target=sensor_update_loop, args=(analogs, stop_event), daemon=True)
    update_thread.start()
    input_thread = threading.Thread(target=input_listener, daemon=True)
    input_thread.start()
    try:
        run()
    finally:
        stop_event.set()
        update_thread.join()

if __name__ == "__main__":
    main()
