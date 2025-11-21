from collections import deque
from .process import ProcessState


class CPUScheduler:
    def __init__(self, quantum=2):
        self.quantum = quantum
        self.ready_queue = deque()
        self.running_process = None
        self.processes = {}

    def add_process(self, process):
        self.processes[process.pid] = process
        process.record_state(ProcessState.READY, "En cola READY")
        self.ready_queue.append(process)
        self._sort_by_priority()

    def _sort_by_priority(self):
        self.ready_queue = deque(sorted(self.ready_queue, key=lambda p: p.priority, reverse=True))

    def schedule_next(self):
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
        return self.running_process

    def get_all_processes(self):
        return list(self.processes.values())
