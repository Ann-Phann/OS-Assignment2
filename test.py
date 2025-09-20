import logging
from mmu import MMU
from page import Page

logger = logging.getLogger(__name__)


class ClockMMU(MMU):
    def __init__(self, frames):
        self.num_disk_reads = 0
        self.num_disk_writes = 0
        self.num_page_faults = 0
        self.frames = frames

        self.page_table = {}  # Page number: Page Object
        self.memory = [None] * frames  # Page number
        self.clock_hand = 0

    def set_debug(self):
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)

    def reset_debug(self):
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.WARNING)

    def read_memory(self, page_number):
        self.access_memory(page_number, False)

    def write_memory(self, page_number):
        self.access_memory(page_number, True)

    def access_memory(self, page_number, write):
        # Page is already in memory
        if page_number in self.page_table:
            logger.debug(f"Access {page_number}\n")
            page = self.page_table[page_number]
            page.use_bit = True  # recently used
            if write:
                page.dirty = True
            return

        # Page fault
        logger.debug(f"Page fault at page {page_number}")
        self.num_page_faults += 1
        self.num_disk_reads += 1

        # Evict least recently used page
        self.evict_page()

        # Load new page into memory
        page = Page(page_number, write)
        page.use_bit = True
        self.page_table[page_number] = page
        # Replace the evicted page with the current one
        self.memory[self.clock_hand] = page_number
        self.clock_hand = (self.clock_hand + 1) % self.frames

        logger.debug(f"Load new page {page_number}\n")

    def evict_page(self):
        while True:
            # Get the page number that clock hand is pointing at
            page_number = self.memory[self.clock_hand]
            if page_number is None:
                break

            page = self.page_table[page_number]
            if page.use_bit:
                logger.debug(f"Clear use bit for page {page_number}")
                page.use_bit = False  # Clear use bit
            else:  # evict not recently used page
                # Write page to disk if the page is marked as dirty/written
                if page.dirty:
                    self.num_disk_writes += 1
                    logger.debug(f"Write page {page_number} to disk")

                del self.page_table[page_number]
                logger.debug(f"Evict page {page_number}")
                break
            self.clock_hand = (self.clock_hand + 1) % self.frames

    def get_total_disk_reads(self):
        return self.num_disk_reads

    def get_total_disk_writes(self):
        return self.num_disk_writes

    def get_total_page_faults(self):
        return self.num_page_faults