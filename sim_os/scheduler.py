from collections import deque
from .process import ProcessState


class CPUScheduler:
    def __init__(self, quantum=2, policy="RR"):
        self.quantum = quantum
        self.ready_queue = deque()
        self.running_process = None
        self.processes = {}
        self.policy = policy

    def add_process(self, process):
        self.processes[process.pid] = process
        process.record_state(ProcessState.READY, "En cola READY")
        self.ready_queue.append(process)
        self._sort_by_policy()

    def _sort_by_policy(self):
        if self.policy == "PRIORITY":
            self.ready_queue = deque(sorted(self.ready_queue, key=lambda p: p.priority))
        elif self.policy == "RR":
            self.ready_queue = deque(list(self.ready_queue))
        elif self.policy == "FIFO":
            self.ready_queue = deque(list(self.ready_queue))
        elif self.policy == "SJF":
            def next_burst(proc):
                return proc.cpu_profile[0] if proc.cpu_profile else 9999
            self.ready_queue = deque(sorted(self.ready_queue, key=next_burst))

    def set_policy(self, policy):
        if policy in {"PRIORITY", "RR", "FIFO", "SJF"}:
            self.policy = policy
            self._sort_by_policy()
            return True
        return False

    def schedule_next(self):
        self._sort_by_policy()
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
