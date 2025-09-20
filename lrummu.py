from mmu import MMU
from collections import OrderedDict

class LruMMU(MMU):
    def __init__(self, frames):
        self.frames = frames
        self.total_disk_read = 0
        self.total_disk_write = 0
        self.total_page_fault = 0
        self.loaded_pages = OrderedDict() 
        self.current_size = 0
        self.debug = False

    def set_debug(self):
        # Implement the method to set debug mode
        self.debug = True

    def reset_debug(self):
        # Implement the method to reset debug mode
        self.debug = False

    def access(self, page_number, is_write):
        if page_number in self.loaded_pages:
            if is_write:
                self.loaded_pages[page_number] = True
            self.loaded_pages.move_to_end(page_number)
            if self.debug:
                print(f"Hit on page {page_number}")
        else:
            self.total_page_fault += 1
            self.total_disk_read += 1
            if self.current_size == self.frames:
                evict_page, dirty = self.loaded_pages.popitem(last=False)
                if dirty:
                    self.total_disk_write += 1
                self.current_size -= 1
                if self.debug:
                    print(f"Evict page {evict_page}")
            self.loaded_pages[page_number] = is_write
            self.loaded_pages.move_to_end(page_number)
            self.current_size += 1
            if self.debug:
                print(f"Load page {page_number}")

    def read_memory(self, page_number):
        # Implement the method to read memory
        self.access(page_number, False)

    def write_memory(self, page_number):
        # Implement the method to write memory
        self.access(page_number, True)

    def get_total_disk_reads(self):
        # Implement the method to get total disk reads
        return self.total_disk_read

    def get_total_disk_writes(self):
        # Implement the method to get total disk writes
        return self.total_disk_write

    def get_total_page_faults(self):
        # Implement the method to get total page faults
        return self.total_page_fault