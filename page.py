class Page:
    def __init__(self, page_number, dirty = False, use_bit=False):
        self.page_number = page_number
        self.dirty = dirty
        self.use_bit = use_bit