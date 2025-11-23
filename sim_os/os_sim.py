from datetime import datetime
import random

from .memory import MemoryManager
from .security import SecurityManager
from .filesystem import FileSystem
from .scheduler import CPUScheduler
from .virtual_memory import VirtualMemoryManager
from .io import IOManager
from .process import Process, ProcessState


class OperatingSystem:
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
        self.log_event("MEMORIA", f"Espacio virtual creado ({pages} páginas) para PID {process.pid}", process=process)
        self.security_manager.store_integrity_hash(f"process_{process.pid}", process.name)
        self.cpu_scheduler.add_process(process)
        self.log_event("PROCESO", f"Creado proceso '{name}' (PID {process.pid})", process=process, metadata={'prioridad': priority})
        self.log_event("MEMORIA", f"Asignados {memory_size} KB a PID {process.pid}", process=process, metadata={'direccion': address})
        return process, f"Proceso '{name}' (PID: {process.pid}) creado exitosamente"

    def kill_process(self, pid):
        process = self.cpu_scheduler.processes.get(pid)
        if not process:
            return False, "Proceso no encontrado"
        if process.memory_address is not None:
            self.memory_manager.deallocate(process.memory_address)
            self.log_event("MEMORIA", f"Liberados {process.memory_size} KB de PID {pid}", process=process, metadata={'direccion': process.memory_address})
            self.virtual_memory.release_space(pid)
        self.log_event("PROCESO", f"Proceso PID {pid} terminado", process=process)
        self.process_archive[pid] = process
        self.cpu_scheduler.remove_process(pid)
        return True, f"Proceso PID {pid} terminado"

    def get_system_info(self):
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

    def trigger_irq(self, device_name, level=1):
        running = self.cpu_scheduler.get_running_process()
        if running and running.state == ProcessState.RUNNING:
            running.record_state(ProcessState.WAITING, f"Interrumpido por IRQ {device_name}")
            self.log_event("CPU", f"IRQ {device_name} nivel {level} interrumpe PID {running.pid}", process=running)
        irq_proc, _ = self.create_process(f"irq_{device_name}", priority=10, memory_size=8)
        if not irq_proc:
            return False, "No se pudo crear proceso IRQ"
        try:
            if irq_proc in self.cpu_scheduler.ready_queue:
                self.cpu_scheduler.ready_queue.remove(irq_proc)
            self.cpu_scheduler.ready_queue.appendleft(irq_proc)
            p = self.run_scheduler_cycle()
            if p:
                self.log_event("CPU", f"Atendida IRQ {device_name}", process=p)
        finally:
            self.kill_process(irq_proc.pid)
        if running:
            running.record_state(ProcessState.READY, "Reanudado tras IRQ")
            self.cpu_scheduler.ready_queue.appendleft(running)
            self.log_event("CPU", f"Reanudando PID {running.pid} tras IRQ {device_name}", process=running)
        return True, f"IRQ {device_name} atendida"

    def log_event(self, category, message, process=None, metadata=None):
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
        if limit is None or limit >= len(self.timeline):
            return list(self.timeline)
        return self.timeline[-limit:]

    def find_process(self, pid):
        return self.cpu_scheduler.processes.get(pid) or self.process_archive.get(pid)

    def get_process_history(self, pid):
        process = self.find_process(pid)
        if not process:
            return None
        return list(process.history)

    def get_process_flow(self, pid):
        process = self.find_process(pid)
        if not process:
            return None
        return process.state_flow
