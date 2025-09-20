import logging
from mmu import MMU
from page import Page


logger = logging.getLogger(__name__)

class ClockMMU(MMU):
    def __init__(self, frames):
        # Constructor logic for EscMMU
        self.total_disk_read = 0
        self.total_disk_write = 0
        self.total_page_fault = 0

        self.frames = frames
        self.page_table = {}
        self.loaded_pages = [None] * frames
        self.clock_hand = 0

    def set_debug(self):
        # Implement the method to set debug mode
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)

    def reset_debug(self):
        # Implement the method to reset debug mode
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.WARNING)

    def access_memory(self, page_number, is_write):
        # Page is already in loaded_pages
        if page_number in self.page_table:
            page = self.page_table[page_number]
            page.use_bit = True  # recently used
            if is_write:
                page.dirty = True

            logger.debug(f"Page hit: {page_number}{' (is_write)' if is_write else ''}\n")
            return

        # Page fault
        self.total_page_fault += 1
        self.total_disk_read += 1
        logger.debug(f"Page fault: {page_number}{' (write)' if is_write else ''}")

        # Evict least recently used page
        self.evict_page()

        # Load new page into loaded_pages
        new_page = Page(page_number, is_write, use_bit=True)
        self.page_table[page_number] = new_page

        # Replace the evicted page with the current one
        self.loaded_pages[self.clock_hand] = page_number
        self.clock_hand = (self.clock_hand + 1) % self.frames

        logger.debug(f"Load new page {page_number}\n")

    def evict_page(self):
        while True:
            # Get the page number that clock hand is pointing at
            evict_page_num = self.loaded_pages[self.clock_hand]
            if evict_page_num is None:
                break

            page = self.page_table[evict_page_num]
            if page.use_bit:
                logger.debug(f"Clear use bit for page {evict_page_num}")
                page.use_bit = False  # Clear use bit
            else:  # evict not recently used page
                # write page to disk if the page is marked as dirty
                if page.dirty:
                    self.total_disk_write += 1
                    logger.debug(f"is_write page {evict_page_num} to disk")

                del self.page_table[evict_page_num]
                logger.debug(f"Evict page {evict_page_num}")
                break
            self.clock_hand = (self.clock_hand + 1) % self.frames


    def read_memory(self, page_number):
        # Implement the method to read loaded_pages
        self.access_memory(page_number, False)

    def write_memory(self, page_number):
        # Implement the method to is_write loaded_pages
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
