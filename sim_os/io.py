from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class IOMode(Enum):
    PROGRAMADO = "Programado"
    DMA = "DMA"


@dataclass
class IODevice:
    name: str
    mode: IOMode = IOMode.PROGRAMADO
    busy: bool = False
    last_request: dict = field(default_factory=dict)


class IOManager:
    def __init__(self):
        self.devices = {
            'disco': IODevice(name='Disco', mode=IOMode.DMA),
            'teclado': IODevice(name='Teclado', mode=IOMode.PROGRAMADO),
            'red': IODevice(name='Red', mode=IOMode.DMA)
        }
        self.interrupt_log = []

    def request_io(self, pid, device_name, duration=1):
        device = self.devices.get(device_name)
        if not device:
            return False, "Dispositivo no reconocido"
        device.busy = True
        device.last_request = {'pid': pid, 'duration': duration, 'timestamp': datetime.now()}
        mode = device.mode.value
        event = f"PID {pid} usa {device.name} en modo {mode}"
        self.interrupt_log.append(event)
        device.busy = False
        return True, event

    def get_status(self):
        summary = []
        for name, dev in self.devices.items():
            summary.append({
                'name': dev.name,
                'mode': dev.mode.value,
                'busy': dev.busy,
                'last_request': dev.last_request
            })
        return summary

    def set_mode(self, device_name, mode_str):
        device = self.devices.get(device_name)
        if not device:
            return False, "Dispositivo no reconocido"
        if mode_str.upper() == "DMA":
            device.mode = IOMode.DMA
        elif mode_str.upper() in {"PROGRAMADO", "PROGRAMMED"}:
            device.mode = IOMode.PROGRAMADO
        else:
            return False, "Modo no reconocido"
        return True, f"Modo de {device.name} cambiado a {device.mode.value}"

    def set_busy(self, device_name, busy):
        device = self.devices.get(device_name)
        if not device:
            return False, "Dispositivo no reconocido"
        device.busy = bool(busy)
        return True, f"{device.name} {'activado' if device.busy else 'desactivado'}"
