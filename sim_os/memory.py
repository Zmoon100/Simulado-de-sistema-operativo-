class MemoryManager:
    def __init__(self, total_memory=1024):
        self.total_memory = total_memory
        self.available_memory = total_memory
        self.allocated_blocks = {}
        self.next_address = 0

    def allocate(self, size, pid):
        if size > self.available_memory:
            return None
        address = self.next_address
        self.allocated_blocks[address] = (size, pid)
        self.available_memory -= size
        self.next_address += size
        return address

    def deallocate(self, address):
        if address in self.allocated_blocks:
            size, pid = self.allocated_blocks[address]
            del self.allocated_blocks[address]
            self.available_memory += size
            return True
        return False

    def get_memory_info(self):
        return {
            'total': self.total_memory,
            'available': self.available_memory,
            'used': self.total_memory - self.available_memory,
            'usage_percent': ((self.total_memory - self.available_memory) / self.total_memory) * 100
        }
