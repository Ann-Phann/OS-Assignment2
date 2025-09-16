from mmu import MMU

class RandMMU(MMU):
    def __init__(self, frames):
        # Constructor logic for RandMMU
        self.total_disk_read = 0
        self.total_disk_write = 0
        self.total_page_fault = 0

        self.page_frame = {}

    def set_debug(self):
        # TODO: Implement the method to set debug mode
        pass

    def reset_debug(self):
        # TODO: Implement the method to reset debug mode
        pass

    def read_memory(self, page_number):
        # TODO: Implement the method to read memory
        pass

    def write_memory(self, page_number):
        # TODO: Implement the method to write memory
        pass

    def get_total_disk_reads(self):
        # TODO: Implement the method to get total disk reads
        return -1

    def get_total_disk_writes(self):
        # TODO: Implement the method to get total disk writes
        return -1

    def get_total_page_faults(self):
        # TODO: Implement the method to get total page faults
        return -1
