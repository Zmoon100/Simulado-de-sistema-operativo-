"""
Simulador de Sistema Operativo en Python
Incluye: Gestión de procesos, memoria, sistema de archivos y planificador de CPU
"""

import os
import time
import threading
from datetime import datetime
from collections import deque
from enum import Enum, auto
from dataclasses import dataclass, field
import json
import random
import hashlib
try:
    from rich.console import Console, Group  # type: ignore
    from rich.table import Table  # type: ignore
    from rich.panel import Panel  # type: ignore
    from rich.text import Text  # type: ignore
    from rich.align import Align  # type: ignore
    from rich import box  # type: ignore
except ImportError:  # pragma: no cover
    Console = None
    Group = None
    Table = None
    Panel = None
    Text = None
    Align = None
    box = None


class ProcessState(Enum):
    """Estados de un proceso"""
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    TERMINATED = "TERMINATED"


class Process:
    """Representa un proceso en el sistema"""
    
    _next_pid = 1
    
    def __init__(self, name, priority=5, memory_size=100, arrival_time=None, cpu_profile=None):
        self.pid = Process._next_pid
        Process._next_pid += 1
        self.name = name
        self.priority = priority  # 1-10, mayor = más prioridad
        self.state = ProcessState.NEW
        self.memory_size = memory_size
        self.memory_address = None
        self.cpu_time = 0
        self.created_at = datetime.now()
        self.arrival_time = arrival_time or datetime.now()
        self.cpu_profile = cpu_profile or self._generate_cpu_profile()
        self.io_profile = self._generate_io_profile()
        self.files = []
        self.history = []
        self.state_flow = []
        self.security_hash = None
        self.virtual_pages = []
        
    def __repr__(self):
        return f"Process(pid={self.pid}, name={self.name}, state={self.state.value}, priority={self.priority})"

    def record_state(self, new_state, note=None):
        """Registra transición para el comando processflow"""
        self.state = new_state
        entry = {
            'time': datetime.now(),
            'state': new_state.value,
            'note': note
        }
        self.state_flow.append(entry)

    def _generate_cpu_profile(self):
        bursts = [random.randint(2, 6) for _ in range(random.randint(2, 4))]
        return bursts

    def _generate_io_profile(self):
        if len(self.cpu_profile) <= 1:
            return []
        return [random.randint(1, 3) for _ in range(len(self.cpu_profile) - 1)]


class MemoryManager:
    """Gestor de memoria del sistema"""
    
    def __init__(self, total_memory=1024):
        self.total_memory = total_memory
        self.available_memory = total_memory
        self.allocated_blocks = {}  # {address: (size, process_pid)}
        self.next_address = 0
        
    def allocate(self, size, pid):
        """Asigna memoria a un proceso"""
        if size > self.available_memory:
            return None
        
        address = self.next_address
        self.allocated_blocks[address] = (size, pid)
        self.available_memory -= size
        self.next_address += size
        return address
    
    def deallocate(self, address):
        """Libera memoria de un proceso"""
        if address in self.allocated_blocks:
            size, pid = self.allocated_blocks[address]
            del self.allocated_blocks[address]
            self.available_memory += size
            return True
        return False
    
    def get_memory_info(self):
        """Retorna información de memoria"""
        return {
            'total': self.total_memory,
            'available': self.available_memory,
            'used': self.total_memory - self.available_memory,
            'usage_percent': ((self.total_memory - self.available_memory) / self.total_memory) * 100
        }


class VirtualMemoryManager:
    """Simula memoria virtual con paginación por demanda"""
    
    def __init__(self, total_frames=64, page_size=16):
        self.page_size = page_size
        self.total_frames = total_frames
        self.free_frames = list(range(total_frames))
        self.frame_table = {}  # frame -> (pid, page)
        self.page_tables = {}  # pid -> {page: frame}
        self.lru_queue = deque()
        self.page_faults = 0
        self.access_log = []
    
    def create_space(self, pid, size_kb):
        pages = max(1, (size_kb + self.page_size - 1) // self.page_size)
        self.page_tables[pid] = {'pages': pages, 'mapping': {}, 'faults': 0}
        return pages
    
    def release_space(self, pid):
        if pid not in self.page_tables:
            return
        mapping = self.page_tables[pid]['mapping']
        for page, frame in list(mapping.items()):
            if frame in self.frame_table:
                del self.frame_table[frame]
            self.free_frames.append(frame)
        del self.page_tables[pid]
    
    def access_page(self, pid, page_number):
        table = self.page_tables.get(pid)
        if not table:
            return False, "Proceso sin espacio virtual"
        if page_number >= table['pages']:
            return False, "Dirección fuera de rango"
        mapping = table['mapping']
        if page_number in mapping:
            frame = mapping[page_number]
            self._touch_frame(frame)
            self.access_log.append((pid, page_number, False))
            return True, f"Acceso a página {page_number} en marco {frame}"
        # Page fault
        table['faults'] += 1
        self.page_faults += 1
        frame = self._get_free_frame(pid, page_number)
        mapping[page_number] = frame
        self.access_log.append((pid, page_number, True))
        return True, f"Page fault -> cargando página {page_number} en marco {frame}"
    
    def _get_free_frame(self, pid, page_number):
        if not self.free_frames:
            victim_frame = self.lru_queue.popleft()
            victim_pid, victim_page = self.frame_table[victim_frame]
            del self.page_tables[victim_pid]['mapping'][victim_page]
            self.frame_table.pop(victim_frame, None)
        else:
            victim_frame = self.free_frames.pop(0)
        self.frame_table[victim_frame] = (pid, page_number)
        self._touch_frame(victim_frame)
        return victim_frame
    
    def _touch_frame(self, frame):
        if frame in self.lru_queue:
            self.lru_queue.remove(frame)
        self.lru_queue.append(frame)
    
    def get_status(self):
        used = self.total_frames - len(self.free_frames)
        return {
            'page_size': self.page_size,
            'frames_total': self.total_frames,
            'frames_used': used,
            'frames_free': len(self.free_frames),
            'page_faults': self.page_faults
        }


@dataclass
class PermissionSet:
    owner: str = "root"
    group: str = "root"
    perms: str = "rwxr-x---"  # estilo rwx


@dataclass
class FileEntry:
    content: str = ""
    permissions: PermissionSet = field(default_factory=PermissionSet)
    hash: str = ""


class FileSystem:
    """Sistema de archivos simulado"""
    
    def __init__(self, security_manager=None):
        self.files = {}  # {path: FileEntry}
        self.directories = {'/': []}
        self.current_directory = '/'
        self.security_manager = security_manager
    
    def create_file(self, filename, content=""):
        """Crea un archivo"""
        path = self._get_full_path(filename)
        if path in self.files:
            return False, "El archivo ya existe"

        owner = self.security_manager.current_user if self.security_manager else "root"
        entry = FileEntry(
            content=content,
            permissions=PermissionSet(owner=owner, group="devs"),
            hash=self._calc_hash(content)
        )
        self.files[path] = entry
        self._add_to_directory(path)
        if self.security_manager:
            self.security_manager.store_integrity_hash(f"file_{path}", content)
        return True, f"Archivo '{filename}' creado"
    
    def read_file(self, filename):
        """Lee un archivo"""
        path = self._get_full_path(filename)
        entry = self.files.get(path)
        if not entry:
            return None, "Archivo no encontrado"
        if not self._has_permission(path, 'r'):
            return None, "Permiso denegado"
        return entry.content, None
    
    def write_file(self, filename, content):
        """Escribe en un archivo"""
        path = self._get_full_path(filename)
        entry = self.files.get(path)
        if not entry:
            return False, "Archivo no encontrado"
        if not self._has_permission(path, 'w'):
            return False, "Permiso denegado"
        entry.content = content
        entry.hash = self._calc_hash(content)
        if self.security_manager:
            self.security_manager.store_integrity_hash(f"file_{path}", content)
        return True, f"Archivo '{filename}' actualizado"
    
    def delete_file(self, filename):
        """Elimina un archivo"""
        path = self._get_full_path(filename)
        entry = self.files.get(path)
        if not entry:
            return False, "Archivo no encontrado"
        if not self._has_permission(path, 'w'):
            return False, "Permiso denegado"
        del self.files[path]
        self._remove_from_directory(path)
        return True, f"Archivo '{filename}' eliminado"
    
    def list_files(self):
        """Lista archivos en el directorio actual"""
        return [f for f in self.files.keys() if f.startswith(self.current_directory)]
    
    def get_file_info(self, path):
        entry = self.files.get(path)
        if not entry:
            return None
        return {
            'path': path,
            'owner': entry.permissions.owner,
            'group': entry.permissions.group,
            'perms': entry.permissions.perms,
            'hash': entry.hash
        }
    
    def _calc_hash(self, content):
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _has_permission(self, path, mode):
        if not self.security_manager:
            return True
        entry = self.files.get(path)
        if not entry:
            return False
        perms = entry.permissions.perms
        user = self.security_manager.current_user
        if user == entry.permissions.owner:
            scope = perms[:3]
        elif self.security_manager.get_user_group(user) == entry.permissions.group:
            scope = perms[3:6]
        else:
            scope = perms[6:]
        mapping = {'r': scope[0] == 'r', 'w': scope[1] == 'w', 'x': scope[2] == 'x'}
        return mapping.get(mode, False)
    
    def _get_full_path(self, filename):
        """Obtiene la ruta completa del archivo"""
        if filename.startswith('/'):
            return filename
        return f"{self.current_directory.rstrip('/')}/{filename}"
    
    def _add_to_directory(self, path):
        """Añade archivo al directorio"""
        dir_path = '/'.join(path.split('/')[:-1]) or '/'
        if dir_path not in self.directories:
            self.directories[dir_path] = []
        filename = path.split('/')[-1]
        if filename not in self.directories[dir_path]:
            self.directories[dir_path].append(filename)
    
    def _remove_from_directory(self, path):
        """Elimina archivo del directorio"""
        dir_path = '/'.join(path.split('/')[:-1]) or '/'
        filename = path.split('/')[-1]
        if dir_path in self.directories and filename in self.directories[dir_path]:
            self.directories[dir_path].remove(filename)


class SecurityManager:
    """Gestión básica de usuarios y autenticación"""
    
    def __init__(self):
        self.users = {
            'root': {'password': 'root', 'group': 'root'},
            'alice': {'password': 'alice', 'group': 'devs'},
            'bob': {'password': 'bob', 'group': 'devs'}
        }
        self.current_user = 'root'
        self.integrity_registry = {}
    
    def authenticate(self, username, password):
        user = self.users.get(username)
        if user and user['password'] == password:
            self.current_user = username
            return True, f"Usuario {username} autenticado"
        return False, "Credenciales inválidas"
    
    def get_user_group(self, username):
        user = self.users.get(username)
        return user['group'] if user else 'guest'
    
    def list_users(self):
        return [{'user': u, 'group': info['group']} for u, info in self.users.items()]
    
    def store_integrity_hash(self, key, content):
        self.integrity_registry[key] = hashlib.sha256(content.encode()).hexdigest()
    
    def verify_integrity(self, key, content):
        expected = self.integrity_registry.get(key)
        if not expected:
            return False, "No hay hash registrado"
        current = hashlib.sha256(content.encode()).hexdigest()
        return (expected == current, "Integridad verificada" if expected == current else "Integridad comprometida")


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
    """Simula dispositivos de E/S"""
    
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


class CPUScheduler:
    """Planificador de CPU (Round-Robin con prioridades)"""
    
    def __init__(self, quantum=2):
        self.quantum = quantum  # Tiempo de CPU por proceso
        self.ready_queue = deque()
        self.running_process = None
        self.processes = {}  # {pid: Process}
        
    def add_process(self, process):
        """Añade un proceso al planificador"""
        self.processes[process.pid] = process
        process.record_state(ProcessState.READY, "En cola READY")
        self.ready_queue.append(process)
        self._sort_by_priority()
        
    def _sort_by_priority(self):
        """Ordena la cola por prioridad"""
        self.ready_queue = deque(sorted(self.ready_queue, key=lambda p: p.priority, reverse=True))
    
    def schedule_next(self):
        """Planifica el siguiente proceso"""
        if self.running_process:
            if self.running_process.state == ProcessState.RUNNING:
                self.running_process.record_state(ProcessState.READY, "Devuelto a READY")
                self.ready_queue.append(self.running_process)
        
        if self.ready_queue:
            self.running_process = self.ready_queue.popleft()
            self.running_process.record_state(ProcessState.RUNNING, "Ejecutando en CPU")
            self.running_process.cpu_time += self.quantum
            return self.running_process
        return None
    
    def remove_process(self, pid):
        """Elimina un proceso del planificador"""
        if pid in self.processes:
            process = self.processes[pid]
            process.record_state(ProcessState.TERMINATED, "Terminado")
            if process in self.ready_queue:
                self.ready_queue.remove(process)
            if self.running_process and self.running_process.pid == pid:
                self.running_process = None
            del self.processes[pid]
            return True
        return False
    
    def get_running_process(self):
        """Retorna el proceso en ejecución"""
        return self.running_process
    
    def get_all_processes(self):
        """Retorna todos los procesos"""
        return list(self.processes.values())


class OperatingSystem:
    """Sistema Operativo Simulado"""
    
    def __init__(self):
        self.memory_manager = MemoryManager(total_memory=1024)
        self.security_manager = SecurityManager()
        self.file_system = FileSystem(security_manager=self.security_manager)
        self.cpu_scheduler = CPUScheduler(quantum=2)
        self.virtual_memory = VirtualMemoryManager(total_frames=64, page_size=16)
        self.io_manager = IOManager()
        self.running = True
        self.start_time = datetime.now()
        self.timeline = []
        self.timeline_step = 1
        self.process_archive = {}
        
    def create_process(self, name, priority=5, memory_size=100):
        """Crea un nuevo proceso"""
        if memory_size > self.memory_manager.available_memory:
            self.log_event("PROCESO", f"Fallo al crear '{name}': memoria insuficiente", metadata={'memoria': memory_size})
            return None, "Memoria insuficiente"
        
        process = Process(name, priority, memory_size)
        process.record_state(ProcessState.NEW, "Proceso creado")
        address = self.memory_manager.allocate(memory_size, process.pid)
        if address is None:
            self.log_event("PROCESO", f"Fallo al asignar memoria a '{name}'", metadata={'memoria': memory_size})
            return None, "Error al asignar memoria"
        
        process.memory_address = address
        pages = self.virtual_memory.create_space(process.pid, memory_size)
        self.log_event(
            "MEMORIA",
            f"Espacio virtual creado ({pages} páginas) para PID {process.pid}",
            process=process
        )
        self.security_manager.store_integrity_hash(f"process_{process.pid}", process.name)
        self.cpu_scheduler.add_process(process)
        self.log_event(
            "PROCESO",
            f"Creado proceso '{name}' (PID {process.pid})",
            process=process,
            metadata={'prioridad': priority}
        )
        self.log_event(
            "MEMORIA",
            f"Asignados {memory_size} KB a PID {process.pid}",
            process=process,
            metadata={'direccion': address}
        )
        return process, f"Proceso '{name}' (PID: {process.pid}) creado exitosamente"
    
    def kill_process(self, pid):
        """Termina un proceso"""
        process = self.cpu_scheduler.processes.get(pid)
        if not process:
            return False, "Proceso no encontrado"
        
        # Liberar memoria
        if process.memory_address is not None:
            self.memory_manager.deallocate(process.memory_address)
            self.log_event(
                "MEMORIA",
                f"Liberados {process.memory_size} KB de PID {pid}",
                process=process,
                metadata={'direccion': process.memory_address}
            )
            self.virtual_memory.release_space(pid)
        
        # Eliminar del planificador
        self.log_event(
            "PROCESO",
            f"Proceso PID {pid} terminado",
            process=process
        )
        self.process_archive[pid] = process
        self.cpu_scheduler.remove_process(pid)
        return True, f"Proceso PID {pid} terminado"
    
    def get_system_info(self):
        """Obtiene información del sistema"""
        uptime = datetime.now() - self.start_time
        memory_info = self.memory_manager.get_memory_info()
        processes = self.cpu_scheduler.get_all_processes()
        
        return {
            'uptime': str(uptime).split('.')[0],
            'memory': memory_info,
            'total_processes': len(processes),
            'running_process': self.cpu_scheduler.get_running_process(),
            'ready_processes': len(self.cpu_scheduler.ready_queue)
        }

    def run_scheduler_cycle(self):
        """Ejecuta un ciclo de CPU simulando ráfagas y E/S"""
        process = self.cpu_scheduler.schedule_next()
        if not process:
            return None
        self.log_event("CPU", f"CPU asignada a PID {process.pid}", process=process)
        vm_table = self.virtual_memory.page_tables.get(process.pid)
        if vm_table:
            page = random.randint(0, vm_table['pages'] - 1)
            ok, message = self.virtual_memory.access_page(process.pid, page)
            self.log_event("MEMORIA", message, process=process)
        if process.io_profile and random.random() > 0.5:
            process.record_state(ProcessState.WAITING, "Solicitud de E/S")
            device = random.choice(list(self.io_manager.devices.keys()))
            success, detail = self.io_manager.request_io(process.pid, device)
            self.log_event("E/S", detail, process=process)
            process.record_state(ProcessState.READY, "Regresa tras E/S")
            self.cpu_scheduler.ready_queue.append(process)
        else:
            process.record_state(ProcessState.READY, "Listo para siguiente quantum")
            self.cpu_scheduler.ready_queue.append(process)
        self.cpu_scheduler.running_process = None
        return process

    def log_event(self, category, message, process=None, metadata=None):
        """Registra eventos en la línea de tiempo"""
        event = {
            'step': self.timeline_step,
            'timestamp': datetime.now(),
            'category': category.upper(),
            'message': message,
            'metadata': metadata or {},
            'pid': process.pid if process else None
        }
        self.timeline_step += 1
        self.timeline.append(event)
        if process:
            process.history.append(event)
    
    def get_timeline(self, limit=None):
        """Obtiene eventos registrados"""
        if limit is None or limit >= len(self.timeline):
            return list(self.timeline)
        return self.timeline[-limit:]
    
    def find_process(self, pid):
        """Busca procesos activos o archivados"""
        return self.cpu_scheduler.processes.get(pid) or self.process_archive.get(pid)
    
    def get_process_history(self, pid):
        """Devuelve la historia de un proceso"""
        process = self.find_process(pid)
        if not process:
            return None
        return list(process.history)

    def get_process_flow(self, pid):
        process = self.find_process(pid)
        if not process:
            return None
        return process.state_flow


class CommandLineInterface:
    """Interfaz de línea de comandos del sistema operativo"""
    
    def __init__(self, os_sim):
        self.os = os_sim
        self.rich_enabled = Console is not None and Table is not None and Panel is not None
        self.console = Console() if self.rich_enabled else None
        self.demo_mode = True  # modo vistoso paso a paso
        self.demo_delay = 0.5
        self.palette = {
            'primary': 'cyan',
            'success': 'green',
            'warning': 'yellow',
            'danger': 'red',
            'muted': 'bright_black'
        }
        self.category_colors = {
            'PROCESO': 'cyan',
            'MEMORIA': 'blue',
            'CPU': 'magenta',
            'ARCHIVO': 'yellow',
            'E/S': 'yellow',
            'SEGURIDAD': 'red',
            'SISTEMA': 'white'
        }
        self.command_styles = {
            'ps': ('cyan', '🧠'),
            'create': ('green', '🌱'),
            'kill': ('red', '💥'),
            'schedule': ('magenta', '🌀'),
            'meminfo': ('blue', '📊'),
            'top': ('magenta', '📈'),
            'vmem': ('blue', '💾'),
            'ioinfo': ('yellow', '🔌'),
            'fsinfo': ('green', '🗂'),
            'timeline': ('yellow', '⏱'),
            'history': ('cyan', '📜'),
            'ls': ('yellow', '📁'),
            'touch': ('yellow', '📝'),
            'cat': ('yellow', '📖'),
            'echo': ('yellow', '✏'),
            'rm': ('red', '🗑'),
            'demo': ('magenta', '🎬'),
            'help': ('white', '❓'),
            'clear': ('white', '🧽'),
            'exit': ('white', '🚪')
        }
        self.current_command = None
        self.current_command_color = self.palette['primary']
        self.stage_index = 0
        self.commands = {
            'help': self._help,
            'ps': self._list_processes,
            'create': self._create_process,
            'kill': self._kill_process,
            'meminfo': self._memory_info,
            'top': self._system_info,
            'vmem': self._virtual_memory_info,
            'processflow': self._process_flow,
            'ioinfo': self._io_info,
            'touch': self._create_file,
            'cat': self._read_file,
            'echo': self._write_file,
            'rm': self._delete_file,
            'ls': self._list_files,
            'schedule': self._run_scheduler,
            'fsinfo': self._fs_info,
            'timeline': self._timeline,
            'history': self._process_history,
            'login': self._login,
            'whoami': self._whoami,
            'security': self._security_status,
            'demo': self._demo_sequence,
            'clear': self._clear,
            'exit': self._exit
        }
        
    def _help(self, args):
        """Muestra ayuda de comandos"""
        help_text = """
=== Simulador de Sistema Operativo ===

COMANDOS DISPONIBLES:

Procesos:
  ps                    - Lista todos los procesos
  create <nombre> [prioridad] [memoria] - Crea un nuevo proceso
  kill <pid>            - Termina un proceso
  processflow <pid>     - Muestra ciclo de vida
  schedule               - Ejecuta el planificador de CPU

Sistema:
  top                   - Muestra información del sistema
  meminfo               - Muestra información de memoria
  vmem                  - Estado de memoria virtual
  ioinfo                - Dispositivos e interrupciones
  timeline [n]          - Muestra últimos eventos
  history <pid>         - Historia detallada de un proceso
  clear                 - Limpia la pantalla

Archivos:
  touch <archivo>       - Crea un archivo vacío
  cat <archivo>         - Muestra el contenido de un archivo
  echo <texto> > <archivo> - Escribe texto en un archivo
  ls                    - Lista archivos
  rm <archivo>          - Elimina un archivo
  fsinfo                - Detalle de permisos

Seguridad:
  login <usuario> <pass>- Autenticación
  whoami                - Usuario actual
  security              - Estado de seguridad
  demo                  - Corre la secuencia guiada
  help                  - Muestra esta ayuda
  exit                  - Sale del simulador
        """
        if not self.rich_enabled:
            return help_text
        
        sections = {
            "Procesos": [
                "`ps` - Lista todos los procesos",
                "`create <nombre> [prioridad] [memoria]` - Crea un proceso",
                "`kill <pid>` - Termina un proceso",
                "`processflow <pid>` - Ciclo de vida",
                "`schedule` - Ejecuta el planificador"
            ],
            "Sistema": [
                "`top` - Información general",
                "`meminfo` - Estado de memoria",
                "`vmem` - Memoria virtual",
                "`ioinfo` - Dispositivos E/S",
                "`timeline [n]` - Últimos eventos",
                "`history <pid>` - Historia de un proceso",
                "`clear` - Limpia la pantalla"
            ],
            "Archivos": [
                "`touch <archivo>` - Crea archivo",
                "`cat <archivo>` - Lee archivo",
                "`echo <texto> > <archivo>` - Escribe archivo",
                "`ls` - Lista archivos",
                "`rm <archivo>` - Elimina archivo",
                "`fsinfo` - Permisos"
            ],
            "Otros": [
                "`login <user> <pass>` - Autenticación",
                "`whoami` - Usuario activo",
                "`security` - Seguridad",
                "`demo` - Secuencia guiada",
                "`help` - Ayuda",
                "`exit` - Salir"
            ]
        }
        
        grid = Table.grid(padding=1)
        grid.add_column(justify="left")
        grid.add_column(justify="left")
        
        for title, commands in sections.items():
            command_list = "\n".join(commands)
            grid.add_row(f"[bold]{title}[/]", command_list)
        
        return Panel(
            grid,
            title="Guía de Comandos",
            border_style=self.palette['primary'],
            box=box.ROUNDED if box else None
        )
    
    def _list_processes(self, args):
        """Lista todos los procesos"""
        self._stage_step("Leyendo cola de procesos", "Consultando planificador")
        processes = self.os.cpu_scheduler.get_all_processes()
        if not processes:
            if self.rich_enabled:
                return Panel("No hay procesos en el sistema", title="Procesos", style="yellow")
            return "No hay procesos en el sistema"
        
        running = self.os.cpu_scheduler.get_running_process()

        if not self.rich_enabled:
            self._stage_step("Generando tabla en texto plano")
            output = "\n=== PROCESOS ===\n"
            output += f"{'PID':<6} {'Nombre':<15} {'Estado':<12} {'Prioridad':<10} {'Memoria':<10} {'CPU Time':<10}\n"
            output += "-" * 70 + "\n"
            for p in processes:
                output += f"{p.pid:<6} {p.name:<15} {p.state.value:<12} {p.priority:<10} {p.memory_size:<10} {p.cpu_time:<10}\n"
            if running:
                output += f"\nProceso en ejecución: PID {running.pid} - {running.name}\n"
            return output
        
        self._stage_step("Construyendo tablero visual", "Ordenando por prioridad")
        table = Table(
            title="Procesos activos",
            show_lines=True,
            header_style="bold cyan",
            box=box.SIMPLE_HEAVY if box else None
        )
        table.add_column("PID", justify="right", style="bold white")
        table.add_column("Nombre", style="bold")
        table.add_column("Estado", style="magenta")
        table.add_column("Prioridad", justify="center")
        table.add_column("Memoria", justify="right")
        table.add_column("CPU Time", justify="right")
        
        state_colors = {
            ProcessState.NEW: "bright_black",
            ProcessState.READY: "green",
            ProcessState.RUNNING: "cyan",
            ProcessState.WAITING: "yellow",
            ProcessState.TERMINATED: "red"
        }
        
        for p in processes:
            table.add_row(
                str(p.pid),
                p.name,
                f"[{state_colors.get(p.state, 'white')}]{p.state.value}[/]",
                str(p.priority),
                f"{p.memory_size} KB",
                f"{p.cpu_time}"
            )
        
        self._print(table)
        
        if running:
            return Panel(
                f"PID {running.pid} • {running.name}\nPrioridad: {running.priority}\nCPU Time: {running.cpu_time}",
                title="Proceso en ejecución",
                title_align="left",
                style="bold green",
                box=box.ROUNDED if box else None
            )
        return None
    
    def _create_process(self, args):
        """Crea un nuevo proceso"""
        if not args:
            return "Uso: create <nombre> [prioridad] [memoria]"
        
        name = args[0]
        priority = int(args[1]) if len(args) > 1 and args[1].isdigit() else 5
        memory = int(args[2]) if len(args) > 2 and args[2].isdigit() else 100
        
        self._stage_step("Preparando proceso", f"{name} • prioridad {priority} • memoria {memory} KB")
        process, message = self.os.create_process(name, priority, memory)
        success = process is not None
        extra = ""
        if success:
            detail = f"PID: {process.pid} • Prioridad: {process.priority} • Memoria: {process.memory_size} KB"
            extra = f"\n{detail}" if self.rich_enabled else f" ({detail})"
            self._stage_step("Proceso creado", detail)
        return self._styled_feedback(message + extra, success)
    
    def _kill_process(self, args):
        """Termina un proceso"""
        if not args or not args[0].isdigit():
            return "Uso: kill <pid>"
        
        pid = int(args[0])
        self._stage_step("Solicitando terminación", f"PID {pid}")
        success, message = self.os.kill_process(pid)
        if success:
            self._stage_step("Proceso terminado", f"PID {pid}")
        return self._styled_feedback(message, success)
    
    def _memory_info(self, args):
        """Muestra información de memoria"""
        self._stage_step("Consultando gestor de memoria")
        info = self.os.memory_manager.get_memory_info()
        if not self.rich_enabled:
            self._stage_step("Imprimiendo datos numéricos")
            output = "\n=== INFORMACIÓN DE MEMORIA ===\n"
            output += f"Memoria Total:     {info['total']} KB\n"
            output += f"Memoria Usada:     {info['used']} KB\n"
            output += f"Memoria Disponible: {info['available']} KB\n"
            output += f"Uso:               {info['usage_percent']:.2f}%\n"
            return output

        self._stage_step("Renderizando panel con barra de uso")
        usage_bar = self._build_usage_bar(info['usage_percent'])
        
        table = Table.grid(expand=True)
        table.add_column(justify="left")
        table.add_column(justify="right")
        table.add_row("Memoria total", f"{info['total']} KB")
        table.add_row("Memoria usada", f"{info['used']} KB")
        table.add_row("Memoria disponible", f"{info['available']} KB")
        table.add_row("Uso", f"{info['usage_percent']:.2f}%")
        table.add_row(" ", usage_bar)
        
        return Panel(table, title="Memoria", border_style="blue", box=box.ROUNDED if box else None)
    
    def _system_info(self, args):
        """Muestra información del sistema"""
        self._stage_step("Recolectando métricas del sistema")
        info = self.os.get_system_info()
        if not self.rich_enabled:
            self._stage_step("Generando resumen en texto plano")
            output = "\n=== INFORMACIÓN DEL SISTEMA ===\n"
            output += f"Tiempo activo:     {info['uptime']}\n"
            output += f"Procesos totales:  {info['total_processes']}\n"
            output += f"Procesos listos:   {info['ready_processes']}\n"
            output += f"Memoria usada:     {info['memory']['usage_percent']:.2f}%\n"
            
            if info['running_process']:
                p = info['running_process']
                output += f"\nProceso en ejecución:\n"
                output += f"  PID: {p.pid}\n"
                output += f"  Nombre: {p.name}\n"
                output += f"  Prioridad: {p.priority}\n"
                output += f"  Tiempo CPU: {p.cpu_time}\n"
            
            return output

        grid = Table.grid(padding=(0, 1))
        grid.add_column(justify="left")
        grid.add_column(justify="left")
        grid.add_row("Tiempo activo", info['uptime'])
        grid.add_row("Procesos totales", str(info['total_processes']))
        grid.add_row("Procesos listos", str(info['ready_processes']))
        grid.add_row("Uso de memoria", f"{info['memory']['usage_percent']:.2f}% {self._build_usage_bar(info['memory']['usage_percent'])}")
        
        panels = [Panel(grid, title="Sistema", border_style="cyan", box=box.ROUNDED if box else None)]
        
        if info['running_process']:
            self._stage_step("Detallando proceso activo")
            p = info['running_process']
            detail = Table.grid(padding=0)
            detail.add_column(justify="left")
            detail.add_row(f"PID: {p.pid}")
            detail.add_row(f"Nombre: {p.name}")
            detail.add_row(f"Prioridad: {p.priority}")
            detail.add_row(f"Tiempo CPU: {p.cpu_time}")
            panels.append(Panel(detail, title="Proceso en ejecución", border_style="green", box=box.ROUNDED if box else None))
        
        return Group(*panels)

    def _virtual_memory_info(self, args):
        """Muestra estado de memoria virtual"""
        self._stage_step("Consultando tabla de páginas")
        status = self.os.virtual_memory.get_status()
        accesses = self.os.virtual_memory.access_log[-5:]
        if not self.rich_enabled:
            self._stage_step("Mostrando resumen virtual en texto")
            lines = [
                "=== MEMORIA VIRTUAL ===",
                f"Tamaño de página: {status['page_size']} KB",
                f"Marcos usados/libres: {status['frames_used']}/{status['frames_total']}",
                f"Fallos de página: {status['page_faults']}",
                "Últimos accesos:"
            ]
            for pid, page, fault in accesses:
                lines.append(f"PID {pid} página {page} {'FAULT' if fault else 'OK'}")
            return "\n".join(lines)
        
        table = Table(title="Memoria Virtual", box=box.ROUNDED if box else None)
        table.add_column("Dato", justify="left", style="bold")
        table.add_column("Valor", justify="right")
        table.add_row("Tamaño página", f"{status['page_size']} KB")
        table.add_row("Marcos usados", str(status['frames_used']))
        table.add_row("Marcos libres", str(status['frames_free']))
        table.add_row("Fallos de página", str(status['page_faults']))
        
        log_table = Table(title="Accesos recientes", box=box.SIMPLE if box else None)
        log_table.add_column("PID")
        log_table.add_column("Página")
        log_table.add_column("Evento")
        for pid, page, fault in accesses:
            log_table.add_row(str(pid), str(page), "FAULT" if fault else "HIT")
        
        return Group(table, log_table)

    def _process_flow(self, args):
        """Muestra diagrama NEW→READY→..."""
        if not args or not args[0].isdigit():
            return "Uso: processflow <pid>"
        pid = int(args[0])
        self._stage_step("Consultando ciclo de vida", f"PID {pid}")
        flow = self.os.get_process_flow(pid)
        if flow is None:
            return self._styled_feedback("Proceso no encontrado", success=False, title="Ciclo de vida")
        if not flow:
            return self._styled_feedback("Sin transiciones registradas aún", success=False, title="Ciclo de vida")
        
        if not self.rich_enabled:
            chain = " -> ".join([entry['state'] for entry in flow])
            return f"PID {pid}: {chain}"
        
        timeline = Table(title=f"Ciclo PID {pid}", box=box.ROUNDED if box else None)
        timeline.add_column("Tiempo")
        timeline.add_column("Estado")
        timeline.add_column("Nota")
        for entry in flow:
            timeline.add_row(
                entry['time'].strftime("%H:%M:%S"),
                entry['state'],
                entry['note'] or "-"
            )
        return timeline

    def _io_info(self, args):
        """Muestra dispositivos de E/S"""
        self._stage_step("Leyendo dispositivos de E/S")
        status = self.os.io_manager.get_status()
        if not self.rich_enabled:
            lines = ["=== DISPOSITIVOS E/S ==="]
            for dev in status:
                lines.append(f"{dev['name']} - {dev['mode']} - {'BUSY' if dev['busy'] else 'Libre'}")
            return "\n".join(lines)
        
        table = Table(title="Dispositivos", box=box.ROUNDED if box else None)
        table.add_column("Dispositivo", style="bold")
        table.add_column("Modo")
        table.add_column("Estado")
        table.add_column("Última solicitud")
        for dev in status:
            last = dev['last_request']
            detail = "-"
            if last:
                detail = f"PID {last['pid']} ({last['duration']}u) {last['timestamp'].strftime('%H:%M:%S')}"
            table.add_row(
                dev['name'],
                dev['mode'],
                "BUSY" if dev['busy'] else "Libre",
                detail
            )
        return table

    def _fs_info(self, args):
        """Muestra permisos e integridad del sistema de archivos"""
        self._stage_step("Auditando sistema de archivos")
        files = [self.os.file_system.get_file_info(path) for path in self.os.file_system.files.keys()]
        files = [f for f in files if f]
        if not files:
            return self._styled_feedback("No hay archivos para auditar", success=False, title="FS")
        if not self.rich_enabled:
            lines = ["=== FS INFO ==="]
            for info in files:
                lines.append(f"{info['path']} {info['perms']} {info['owner']}:{info['group']}")
            return "\n".join(lines)
        
        table = Table(title="Permisos y Hashes", box=box.SIMPLE_HEAVY if box else None)
        table.add_column("Ruta", style="bold")
        table.add_column("Propietario")
        table.add_column("Grupo")
        table.add_column("Permisos")
        table.add_column("Hash SHA256")
        for info in files:
            table.add_row(info['path'], info['owner'], info['group'], info['perms'], info['hash'][:12] + "...")
        return table

    def _timeline(self, args):
        """Muestra la línea de tiempo de eventos"""
        limit = None
        if args and args[0].isdigit():
            limit = int(args[0])
        self._stage_step("Recuperando eventos", f"Últimos {limit or 'todos'} registros")
        events = self.os.get_timeline(limit)
        if not events:
            return self._styled_feedback("Aún no hay eventos registrados", success=False, title="Timeline")
        
        if not self.rich_enabled:
            self._stage_step("Mostrando timeline en texto plano")
            lines = ["=== TIMELINE ==="]
            for e in events:
                timestamp = e['timestamp'].strftime("%H:%M:%S")
                lines.append(f"[{e['step']}] {timestamp} {e['category']}: {e['message']}")
            return "\n".join(lines)
        
        self._stage_step("Construyendo timeline animado")
        table = Table(
            title="Línea de tiempo",
            box=box.SIMPLE_HEAVY if box else None,
            header_style="bold white",
            row_styles=["dim", "none"]
        )
        table.add_column("#", justify="right")
        table.add_column("Hora")
        table.add_column("Tipo")
        table.add_column("Detalle")
        
        for e in events:
            color = self.category_colors.get(e['category'], 'white')
            timestamp = e['timestamp'].strftime("%H:%M:%S")
            detail = e['message']
            if e['pid']:
                detail += f" [PID {e['pid']}]"
            table.add_row(
                str(e['step']),
                timestamp,
                f"[{color}]{e['category']}[/]",
                detail
            )
        
        return table

    def _process_history(self, args):
        """Muestra la historia de un proceso"""
        if not args or not args[0].isdigit():
            return "Uso: history <pid>"
        
        pid = int(args[0])
        self._stage_step("Buscando proceso", f"PID {pid}")
        history = self.os.get_process_history(pid)
        if history is None:
            return self._styled_feedback(f"No se encontró el proceso {pid}", success=False, title="Historial")
        if not history:
            return self._styled_feedback(f"El proceso {pid} no tiene eventos registrados aún", success=False, title="Historial")
        
        if not self.rich_enabled:
            self._stage_step("Presentando historial en texto plano")
            lines = [f"=== HISTORIAL PID {pid} ==="]
            for e in history:
                timestamp = e['timestamp'].strftime("%H:%M:%S")
                lines.append(f"[{e['step']}] {timestamp} {e['category']}: {e['message']}")
            return "\n".join(lines)
        
        self._stage_step("Componiendo línea de tiempo individual")
        table = Table(
            title=f"Historia del proceso {pid}",
            box=box.ROUNDED if box else None,
            row_styles=["dim", "none"]
        )
        table.add_column("#", justify="right")
        table.add_column("Hora")
        table.add_column("Evento")
        
        for e in history:
            timestamp = e['timestamp'].strftime("%H:%M:%S")
            color = self.category_colors.get(e['category'], 'white')
            table.add_row(
                str(e['step']),
                timestamp,
                f"[{color}]{e['message']}[/]"
            )
        
        return table

    def _demo_sequence(self, args):
        """Ejecuta una secuencia guiada que recorre cada subsistema"""
        self._stage_step("Preparando demo", "Se crearán procesos y archivos temporales")
        # Asegurar que el archivo de demo no exista
        try:
            self.os.file_system.delete_file("demo_log.txt")
        except Exception:
            pass
        
        script = [
            ("Autenticamos al usuario de demo", "login", ["alice", "alice"]),
            ("Mostramos el usuario activo", "whoami", []),
            ("Creamos un proceso web de alta prioridad", "create", ["web", "8", "256"]),
            ("Creamos un proceso de sensores", "create", ["sensor", "5", "128"]),
            ("Listamos procesos para ver NEW→READY", "ps", []),
            ("Consultamos memoria física", "meminfo", []),
            ("Revisamos memoria virtual (paginación/LRU)", "vmem", []),
            ("Ejecutamos el planificador para ver RUNNING y E/S", "schedule", []),
            ("Mostramos el ciclo de vida del proceso web", "processflow", ["{web}"]),
            ("Inspeccionamos dispositivos de E/S", "ioinfo", []),
            ("Creamos un archivo de log de demo", "touch", ["demo_log.txt"]),
            ("Escribimos en el log (simula E/S a disco)", "echo", ["Sistema", "en", "demo", ">", "demo_log.txt"]),
            ("Leemos el log con verificación de integridad", "cat", ["demo_log.txt"]),
            ("Auditamos permisos y hashes del sistema de archivos", "fsinfo", []),
            ("Mostramos la línea de tiempo reciente", "timeline", ["12"])
        ]
        
        context = {}
        for idx, (description, command, raw_args) in enumerate(script, start=1):
            if command == "demo":
                continue
            panel = self._stage_panel(
                f"DEMO Paso {idx}",
                description,
                icon="🎬",
                color="magenta"
            )
            self._print(panel)
            resolved_args = self._resolve_demo_args(raw_args, context)
            self._start_command_visual(command, resolved_args)
            try:
                handler = self.commands.get(command)
                if not handler:
                    self._print(self._styled_feedback(f"Comando desconocido en demo: {command}", success=False, title="Demo"))
                    continue
                result = handler(resolved_args)
                if result is not None:
                    self._print(result)
            except Exception as exc:
                self._print(self._styled_feedback(f"Demo interrumpida: {exc}", success=False, title="Demo"))
                break
            finally:
                self._end_command_visual(command)
            if command == "create" and resolved_args:
                pid = self._get_pid_by_name(resolved_args[0])
                if pid:
                    context[resolved_args[0]] = pid
            self._demo_pause()
        
        return self._styled_feedback("Demo completada. Usa 'timeline' o 'history' para seguir explorando.", success=True, title="Demo")

    def _resolve_demo_args(self, raw_args, context):
        resolved = []
        for arg in raw_args:
            if arg.startswith("{") and arg.endswith("}"):
                key = arg[1:-1]
                value = context.get(key)
                resolved.append(str(value) if value is not None else key)
            else:
                resolved.append(arg)
        return resolved

    def _get_pid_by_name(self, name):
        processes = self.os.cpu_scheduler.get_all_processes()
        matches = [p for p in processes if p.name == name]
        if not matches:
            return None
        matches.sort(key=lambda p: p.created_at, reverse=True)
        return matches[0].pid
    
    def _create_file(self, args):
        """Crea un archivo"""
        if not args:
            return "Uso: touch <archivo>"
        
        self._stage_step("Creando archivo", args[0])
        success, message = self.os.file_system.create_file(args[0])
        if success:
            self.os.log_event("ARCHIVO", f"Creado archivo '{args[0]}'")
            self._stage_step("Archivo listo", args[0])
        return self._styled_feedback(message, success)
    
    def _read_file(self, args):
        """Lee un archivo"""
        if not args:
            return "Uso: cat <archivo>"
        
        self._stage_step("Leyendo archivo", args[0])
        content, error = self.os.file_system.read_file(args[0])
        if error:
            return self._styled_feedback(error, success=False)
        self.os.log_event("ARCHIVO", f"Leído archivo '{args[0]}'")
        self._stage_step("Contenido cargado", f"{len(content or '')} caracteres")
        integrity_note = ""
        if self.os.security_manager:
            key = f"file_{self.os.file_system._get_full_path(args[0])}"
            ok, msg = self.os.security_manager.verify_integrity(key, content or "")
            integrity_note = f"\nIntegridad: {msg}"
        if self.rich_enabled:
            body = content if content else "[bright_black](archivo vacío)"
            return Panel(body, title=f"Archivo: {args[0]}", border_style=self.palette['primary'], box=box.ROUNDED if box else None)
        return (content if content else "(archivo vacío)") + integrity_note
    
    def _write_file(self, args):
        """Escribe en un archivo"""
        if len(args) < 3 or args[-2] != '>':
            return "Uso: echo <texto> > <archivo>"
        
        text = ' '.join(args[:-2])
        filename = args[-1]
        self._stage_step("Escribiendo archivo", f"{filename} ({len(text)} caracteres)")
        success, message = self.os.file_system.write_file(filename, text)
        if success:
            self.os.log_event("ARCHIVO", f"Actualizado archivo '{filename}'", metadata={'longitud': len(text)})
            self._stage_step("Escritura completada", filename)
        return self._styled_feedback(message, success)
    
    def _delete_file(self, args):
        """Elimina un archivo"""
        if not args:
            return "Uso: rm <archivo>"
        
        self._stage_step("Eliminando archivo", args[0])
        success, message = self.os.file_system.delete_file(args[0])
        if success:
            self.os.log_event("ARCHIVO", f"Eliminado archivo '{args[0]}'")
            self._stage_step("Archivo eliminado", args[0])
        return self._styled_feedback(message, success)

    def _login(self, args):
        """Autentica a un usuario"""
        if len(args) < 2:
            return "Uso: login <usuario> <password>"
        self._stage_step("Verificando credenciales", args[0])
        success, message = self.os.security_manager.authenticate(args[0], args[1])
        self.os.log_event("SEGURIDAD", f"Login de {args[0]}: {'OK' if success else 'Fallo'}")
        return self._styled_feedback(message, success, title="Login")

    def _whoami(self, args):
        """Usuario actual"""
        user = self.os.security_manager.current_user
        group = self.os.security_manager.get_user_group(user)
        self._stage_step("Usuario activo", user)
        return f"{user} ({group})"

    def _security_status(self, args):
        """Resumen de seguridad"""
        sec = self.os.security_manager
        self._stage_step("Compilando estado de seguridad")
        users = sec.list_users()
        registry = sec.integrity_registry
        if not self.rich_enabled:
            lines = [f"Usuario actual: {sec.current_user}"]
            lines.append("Usuarios:")
            for u in users:
                lines.append(f" - {u['user']} ({u['group']})")
            lines.append(f"Hashes registrados: {len(registry)}")
            return "\n".join(lines)
        
        user_table = Table(title="Usuarios", box=box.ROUNDED if box else None)
        user_table.add_column("Usuario")
        user_table.add_column("Grupo")
        for u in users:
            user_table.add_row(u['user'], u['group'])
        
        hash_table = Table(title="Integridad registrada", box=box.SIMPLE if box else None)
        hash_table.add_column("Clave")
        hash_table.add_column("Hash")
        if registry:
            for key, value in registry.items():
                hash_table.add_row(key, value[:16] + "...")
        else:
            hash_table.add_row("-", "Sin registros")
        
        header = Panel.fit(
            f"[bold]{sec.current_user}[/] conectado",
            border_style=self.palette['primary'],
            box=box.ROUNDED if box else None
        )
        return Group(header, user_table, hash_table)
    
    def _list_files(self, args):
        """Lista archivos"""
        self._stage_step("Escaneando sistema de archivos", "Consultando directorio actual")
        files = self.os.file_system.list_files()
        if not files:
            return self._styled_feedback("No hay archivos", success=False, title="Archivos")
        if not self.rich_enabled:
            self._stage_step("Mostrando listado en texto plano")
            return "\n".join(files)
        
        self._stage_step("Construyendo tabla ilustrativa")
        table = Table(title="Archivos en el directorio actual", box=box.SIMPLE_HEAVY if box else None)
        table.add_column("Ruta", style="bold white")
        table.add_column("Permisos")
        table.add_column("Owner")
        for path in files:
            info = self.os.file_system.get_file_info(path) or {}
            table.add_row(path, info.get('perms', '---'), info.get('owner', '?'))
        return table
    
    def _run_scheduler(self, args):
        """Ejecuta el planificador"""
        self._stage_step("Invocando planificador", "Aplicando round-robin")
        process = self.os.run_scheduler_cycle()
        if not process:
            if self.rich_enabled:
                return Panel("No hay procesos para planificar", title="Planificador", style="yellow")
            return "No hay procesos para planificar"
        
        self.os.log_event(
            "CPU",
            f"Quantum asignado a PID {process.pid}",
            process=process,
            metadata={'cpu_time': process.cpu_time}
        )
        
        if not self.rich_enabled:
            return f"Planificando proceso: PID {process.pid} - {process.name} (Tiempo CPU: {process.cpu_time})"

        bar = self._build_usage_bar(min(process.cpu_time, 100), width=20, color="cyan")
        self._stage_step("Mostrando panel del planificador", f"PID {process.pid}")
        return Panel(
            f"PID {process.pid} - {process.name}\nPrioridad: {process.priority}\nCPU acumulado: {process.cpu_time}\n{bar}",
            title="Planificador",
            border_style="magenta",
            box=box.ROUNDED if box else None
        )
    
    def _clear(self, args):
        """Limpia la pantalla"""
        if self.console:
            self.console.clear()
        else:
            os.system('cls' if os.name == 'nt' else 'clear')
        return ""
    
    def _exit(self, args):
        """Sale del simulador"""
        self.os.running = False
        return "Saliendo del simulador..."
    
    def run(self):
        """Inicia la interfaz de línea de comandos"""
        self._render_banner()
        self._print("Escribe 'help' para ver los comandos disponibles\n")
        
        while self.os.running:
            try:
                command_input = input("OS> ").strip()
                if not command_input:
                    continue
                
                parts = command_input.split()
                command = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []
                
                if command in self.commands:
                    self._start_command_visual(command, args)
                    result = self.commands[command](args)
                    if result is not None:
                        self._print(result)
                    self._end_command_visual(command)
                else:
                    self._print(self._styled_feedback("Comando no reconocido. Escribe 'help' para ayuda.", success=False, title="Error"))
                    
            except KeyboardInterrupt:
                self._print("\n\nSaliendo del simulador...")
                self.os.running = False
            except Exception as e:
                self._print(f"[red]Error: {e}[/]" if self.rich_enabled else f"Error: {e}")

    def _build_usage_bar(self, percent, width=30, color="blue"):
        """Construye una barra de uso porcentual"""
        percent = max(0, min(100, float(percent)))
        filled = int((percent / 100) * width)
        empty = width - filled
        return f"[{color}]" + "█" * filled + "[/]" + "·" * empty + f" {percent:.1f}%"

    def _styled_feedback(self, message, success=True, title=None):
        """Devuelve mensajes con estilo uniforme"""
        if not self.rich_enabled:
            prefix = "✔ " if success else "✖ "
            return f"{prefix}{message}"
        style = self.palette['success'] if success else self.palette['danger']
        panel_title = title or ("Éxito" if success else "Error")
        return Panel(
            message,
            title=panel_title,
            border_style=style,
            box=box.ROUNDED if box else None
        )

    def _render_banner(self):
        """Muestra encabezado vistoso"""
        if not self.rich_enabled:
            self._print("=" * 60)
            self._print("  SIMULADOR DE SISTEMA OPERATIVO")
            self._print("=" * 60)
            return
        
        banner_text = "[bold cyan]SIMULADOR DE SISTEMA OPERATIVO[/]\n[bright_black]Gestión de procesos • Memoria • Archivos • CPU[/]"
        panel = Panel(
            banner_text,
            border_style=self.palette['primary'],
            padding=(1, 2),
            box=box.DOUBLE if box else None
        )
        self._print(panel)

    def _start_command_visual(self, command, args):
        """Muestra etapa inicial del comando"""
        if not self.demo_mode:
            return
        self.current_command = command
        self.stage_index = 0
        self.current_command_color, icon = self.command_styles.get(
            command, (self.palette['primary'], '⚙')
        )
        arg_text = " ".join(args) if args else "Sin parámetros"
        panel = self._stage_panel(
            f"Iniciando {command.upper()}",
            arg_text,
            icon=icon,
            color=self.current_command_color
        )
        self._print(panel)
        self._demo_pause()

    def _end_command_visual(self, command):
        """Marca finalización del comando"""
        if not self.demo_mode:
            return
        icon = self.command_styles.get(command, (None, '✔'))[1]
        panel = self._stage_panel(
            f"{command.upper()} completado",
            "Salida mostrada arriba",
            icon="✔",
            color=self.current_command_color
        )
        self._print(panel)
        self._demo_pause()
        self.current_command = None

    def _stage_panel(self, title, subtitle, icon="▶", color=None):
        """Construye paneles de etapas"""
        color = color or self.palette['primary']
        if not self.rich_enabled:
            return f"{icon} {title} — {subtitle}"
        body = Text()
        body.append(f"{icon} {title}\n", style=f"bold {color}")
        body.append(subtitle, style="bright_black")
        return Panel.fit(
            Align.center(body),
            border_style=color,
            box=box.ROUNDED if box else None
        )

    def _stage_step(self, title, subtitle=""):
        """Paso intermedio durante un comando"""
        if not self.demo_mode:
            return
        self.stage_index += 1
        prefix = f"Paso {self.stage_index}"
        if not subtitle:
            subtitle = ""
        if not self.rich_enabled:
            self._print(f"{prefix}: {title} {('- ' + subtitle) if subtitle else ''}")
            self._demo_pause()
            return
        text = f"{title}\n[bright_black]{subtitle}" if subtitle else title
        color = self.current_command_color if self.current_command else self.palette['muted']
        self._print(
            Panel.fit(
                f"[bold]{prefix}[/]\n{text}",
                border_style=color,
                box=box.SIMPLE if box else None
            )
        )
        self._demo_pause()

    def _demo_pause(self):
        """Pausa breve para visibilidad"""
        if self.demo_mode:
            time.sleep(self.demo_delay)

    def _print(self, message):
        """Imprime usando Rich si está disponible"""
        if self.console:
            self.console.print(message)
        else:
            print(message)


def main():
    """Función principal"""
    os_sim = OperatingSystem()
    cli = CommandLineInterface(os_sim)
    cli.run()


if __name__ == "__main__":
    main()