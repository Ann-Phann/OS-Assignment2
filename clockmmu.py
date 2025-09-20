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
        self.loaded_pages = []
        self.clock_hand = 0

    def set_debug(self):
        # Implement the method to set debug mode
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)

    def reset_debug(self):
        # Implement the method to reset debug mode
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.WARNING)

    def access_memory(self, page_number, is_write):
        # page hit 
        if page_number in self.page_table:
            # get Page object
            page: Page = self.page_table[page_number]
            page.use_bit = True

            if is_write:
                page.dirty = True
            logger.debug(f"Page hit: {page_number}{' (write)' if is_write else ''}\n")
            return
        
        # page fault
        self.total_disk_read += 1
        self.total_page_fault += 1
        logger.debug(f"Page fault: {page_number}{' (write)' if is_write else ''}")

        if len(self.loaded_pages) < self.frames:
            new_page = Page(page_number, dirty=is_write, use_bit = True)
            self.loaded_pages.append(new_page)
            self.page_table[page_number] = new_page
        else:
            while True:
                # get the page object the clock is pointing at 
                evict_page_num = self.loaded_pages[self.clock_hand]
                if evict_page_num is None:
                    break
                evict_page = self.page_table[evict_page_num]

                # check the use bit 
                if evict_page.use_bit == False: # found the one to evict 
      
                    if evict_page.dirty == True:
                        self.total_disk_write += 1
                        logger.debug(f"Saving dirty page {evict_page_num} to disk")

                    # evict the old page
                    del self.page_table[evict_page_num]
                    self.loaded_pages[self.clock_hand] = page_number # overwrite the new page number

                    # load the new page
                    new_page = Page(page_number, dirty=is_write, use_bit=True)
                    self.page_table[page_number] = new_page
                    logger.debug(f"Evicting page {evict_page_num}, Loading new page {page_number}")

                    # move the clock 
                    self.clock_hand = (self.clock_hand + 1) % self.frames
                    break

                # give second chance 
                else:
                    evict_page.use_bit = False
                    self.clock_hand = (self.clock_hand + 1) % self.frames


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
