import customtkinter as ctk
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts

class AdvancedToolsView(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(header, text="Advanced Tools & Legacy Studios", font=Fonts.heading1()).pack(side="left")

        # Grid Container
        grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)

        tools = [
            ("Coloring Book Studio", "ColoringStudioView", "Legacy tool for coloring books."),
            ("Planner Studio", "PlannerStudioView", "Legacy tool for planners."),
            ("Story Book Studio", "StoryBookStudioView", "Legacy tool for story books."),
            ("Activity Book Studio", "ActivityBookStudioView", "Legacy tool for activity books."),
            ("Notebook Studio", "NotebookStudioView", "Legacy tool for notebooks."),
            ("Journal Studio", "JournalStudioView", "Legacy tool for journals."),
            ("Interior Designer", "InteriorDesignerView", "Low-level interior editor."),
            ("Scene Builder", "SceneBuilderView", "Low-level scene composition."),
            ("Prompt Generator", "PromptGeneratorView", "Raw AI prompt engineering."),
            ("Metadata", "MetadataView", "Raw KDP metadata editor."),
            ("Export Center", "ExportCenterView", "Standalone PDF exporter."),
            ("KDP Compliance", "KDPComplianceView", "Standalone QA inspection.")
        ]

        row, col = 0, 0
        for name, view_class, desc in tools:
            card = ctk.CTkFrame(grid_frame, fg_color=Colors.BG_CARD)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            
            ctk.CTkLabel(card, text=name, font=Fonts.heading3()).pack(anchor="w", padx=15, pady=(15, 5))
            ctk.CTkLabel(card, text=desc, font=Fonts.body(), text_color="gray").pack(anchor="w", padx=15, pady=(0, 15))
            
            btn = ctk.CTkButton(card, text="Launch", command=lambda v=name: self.app.show_view(v))
            btn.pack(anchor="w", padx=15, pady=(0, 15))

            col += 1
            if col > 2:
                col = 0
                row += 1
                
        for i in range(3):
            grid_frame.grid_columnconfigure(i, weight=1)
