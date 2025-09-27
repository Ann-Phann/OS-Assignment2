from mmu import MMU
import logging
from page import Page

logger = logging.getLogger(__name__)


class OptimalMMU(MMU):
    def __init__(self, frames):
        self.total_disk_read = 0
        self.total_disk_write = 0
        self.total_page_fault = 0

        self.frames = frames
        self.page_table = {}
        self.memory = []

    def access_memory(self, page_number, current_index, future_access, is_write):
        # page hit
        if page_number in self.page_table:
            # get Page object
            page: Page = self.page_table[page_number]
            if is_write:
                page.dirty = True
            logger.debug(f"Page hit: {page_number}{' (write)' if is_write else ''}\n")
            return
        
        # page fault
        self.total_disk_read += 1
        self.total_page_fault += 1
        logger.debug(f"Page fault: {page_number}{' (write)' if is_write else ''}")

        self.evict_page(current_index, future_access)

        # load new page to memory
        new_page = Page(page_number, dirty=is_write)
        self.page_table[page_number] = new_page
        self.memory.append(page_number)
        logger.debug(f"Loading new page {page_number}")

    def evict_page(self, current_index, future_access):
        if len(self.memory) < self.frames:
            return  # No need to evict if there's still space

        # Find the page to evict using the optimal algorithm
        farthest_index = -1
        page_to_evict = None

        for page_num in self.memory:
            # clean up past access
            while future_access[page_num] and future_access[page_num][0] <= current_index:
                future_access[page_num].pop(0)

            # find the next use of this page
            if future_access[page_num]:
                next_use_index = future_access[page_num][0]
            else:
                next_use_index = float('inf')  # Page not used again

            if next_use_index > farthest_index:
                farthest_index = next_use_index
                page_to_evict = page_num

        
        # Evict the page
        evicted_page = self.page_table[page_to_evict]
        if evicted_page.dirty:
            self.total_disk_write += 1
            logger.debug(f"Writing dirty page {page_to_evict} to disk")
        del self.page_table[page_to_evict]
        self.memory.remove(page_to_evict)
        logger.debug(f"Evict page {page_to_evict}")


    def read_memory(self, page_number, current_index, future_access):
        self.access_memory(page_number, current_index, future_access, is_write=False)

    def write_memory(self, page_number, current_index, future_access):
        self.access_memory(page_number, current_index, future_access, is_write=True)

    def set_debug(self):
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)


    def reset_debug(self):
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.WARNING)

    def get_total_disk_reads(self):
        return self.total_disk_read

    def get_total_disk_writes(self):
        return self.total_disk_write

    def get_total_page_faults(self):
        return self.total_page_fault