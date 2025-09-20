class Page:
    def __init__(self, page_number, dirty = False):
        self.page_number = page_number
        self.dirty = False
        self.bit_use = False