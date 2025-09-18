import logging
import random

from mmu import MMU
from page import Page

logger = logging.getLogger(__name__)

class RandMMU(MMU):
    def __init__(self, frames):
        # Constructor logic for RandMMU
        self.total_disk_read = 0
        self.total_disk_write = 0
        self.total_page_fault = 0

        self.frames = frames # number of frames
        self.page_table = {} # dictionary: memory track which pages are loaded - page number: Page object
        self.loaded_pages = [] # using a list for random selection

    def set_debug(self):
        # Implement the method to set debug mode
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)

    def reset_debug(self):
        # Implement the method to reset debug mode
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.WARNING)
    
    def access_memory(self, page_number, is_write: bool):
        # case 1: page hit 
        if page_number in self.page_table:
            page_obj = self.page_table[page_number]

            # if is_write = true, mark page as dirty
            if is_write:
                page_obj.dirty = True
                logger.debug(f"Page hit: {page_number}{' (write)' if is_write else ''}")
            return
            
        
        # case 2: page fault
        logger.debug(f"Page fault: {page_number}{' (write)' if is_write else ''}")
        self.total_page_fault += 1
        self.total_disk_read += 1


        if len(self.loaded_pages) >= self.frames:
            # evict a page randomly
            evict_page_num = random.choice(self.loaded_pages)
            evict_page_num_obj = self.page_table[evict_page_num]

            if evict_page_num_obj.dirty:
                self.total_disk_write += 1
                logger.debug(f"Saving dirty page {evict_page_num} to disk")

            self.loaded_pages.remove(evict_page_num)
            del self.page_table[evict_page_num]
            logger.debug(f"Evicting page {evict_page_num}")

        # load new page into, even with enough memory or have to evict
        new_page_obj = Page(page_number, is_write)
        self.page_table[page_number] = new_page_obj
        self.loaded_pages.append(page_number)

    def read_memory(self, page_number):
        # Implement the method to read memory
        self.access_memory(page_number, False)

    def write_memory(self, page_number):
        # Implement the method to write memory
        self.access_memory(page_number, True)

    def get_total_disk_reads(self):
        # Implement the method to get total disk reads
        return self.total_disk_read

    def get_total_disk_writes(self):
        # Implement the method to get total disk writes
        return self.total_disk_write

    def get_total_page_faults(self):
        # Implement the method to get total page faults
        return self.total_page_fault
