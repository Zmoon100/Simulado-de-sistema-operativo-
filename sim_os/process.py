from datetime import datetime
from enum import Enum
import random


class ProcessState(Enum):
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    TERMINATED = "TERMINATED"


class Process:
    _next_pid = 1

    def __init__(self, name, priority=5, memory_size=100, arrival_time=None, cpu_profile=None):
        self.pid = Process._next_pid
        Process._next_pid += 1
        self.name = name
        self.priority = priority
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
