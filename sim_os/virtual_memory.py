from collections import deque, OrderedDict


class VirtualMemoryManager:
    def __init__(self, total_frames=64, page_size=16):
        self.page_size = page_size
        self.total_frames = total_frames
        self.free_frames = list(range(total_frames))
        self.frame_table = {}
        self.page_tables = {}
        self.lru_queue = deque()
        self.page_faults = 0
        self.access_log = []
        self.tlb_capacity = 4
        self.tlb = OrderedDict()
        self.tlb_hits = 0
        self.tlb_misses = 0

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

    def set_tlb_capacity(self, capacity):
        self.tlb_capacity = max(1, int(capacity))
        while len(self.tlb) > self.tlb_capacity:
            self.tlb.popitem(last=False)

    def reset_tlb(self):
        self.tlb.clear()
        self.tlb_hits = 0
        self.tlb_misses = 0

    def tlb_access(self, pid, page):
        key = (pid, page)
        if key in self.tlb:
            self.tlb.move_to_end(key)
            self.tlb_hits += 1
            return True, f"TLB HIT pid={pid} page={page}"
        self.tlb_misses += 1
        self.tlb[key] = True
        if len(self.tlb) > self.tlb_capacity:
            victim_key, _ = self.tlb.popitem(last=False)
            return False, f"TLB MISS pid={pid} page={page} -> evict pid={victim_key[0]} page={victim_key[1]}"
        return False, f"TLB MISS pid={pid} page={page}"

    def get_tlb_status(self):
        order = list(self.tlb.keys())
        return {
            'capacity': self.tlb_capacity,
            'size': len(self.tlb),
            'order': order,
            'hits': self.tlb_hits,
            'misses': self.tlb_misses
        }
