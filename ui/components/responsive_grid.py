import customtkinter as ctk

class ResponsiveGrid(ctk.CTkScrollableFrame):
    def __init__(self, master, item_width=160, item_height=200, **kwargs):
        super().__init__(master, **kwargs)
        self.item_width = item_width
        self.item_height = item_height
        self.items = []
        
        self.bind("<Configure>", self._on_resize)
        
    def add_item(self, widget):
        self.items.append(widget)
        self._reflow()
        
    def clear(self):
        for widget in self.items:
            widget.destroy()
        self.items = []
        
    def _on_resize(self, event=None):
        self._reflow()
        
    def _reflow(self):
        if not self.items:
            return
            
        # Get actual width of the scrollable inner frame
        width = self.winfo_width()
        # Account for scrollbar width approx 20px
        available_width = width - 25
        
        if available_width < self.item_width:
            columns = 1
        else:
            columns = available_width // self.item_width
            
        for i, widget in enumerate(self.items):
            row = i // columns
            col = i % columns
            widget.grid(row=row, column=col, padx=10, pady=10, sticky="n")
