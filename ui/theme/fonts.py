import customtkinter as ctk

class Fonts:
    @staticmethod
    def get_font(size=12, weight="normal"):
        return ctk.CTkFont(family="Roboto", size=size, weight=weight)
        
    @staticmethod
    def heading1():
        return Fonts.get_font(size=28, weight="bold")
        
    @staticmethod
    def heading2():
        return Fonts.get_font(size=22, weight="bold")
        
    @staticmethod
    def heading3():
        return Fonts.get_font(size=18, weight="bold")
        
    @staticmethod
    def body():
        return Fonts.get_font(size=14, weight="normal")
        
    @staticmethod
    def body_bold():
        return Fonts.get_font(size=14, weight="bold")
        
    @staticmethod
    def small():
        return Fonts.get_font(size=11, weight="normal")
