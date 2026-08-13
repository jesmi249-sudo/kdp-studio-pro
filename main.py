import os
import sys
import traceback
import time
import customtkinter as ctk
from core.logger import get_logger

logger = get_logger(__name__)

def main():
    logger.info("Starting KDP Studio Pro")
    try:
        # Create a root instance but hide it immediately
        root = ctk.CTk()
        root.withdraw()
        
        # Show Splash Screen
        from ui.splash import SplashScreen
        splash = SplashScreen(master=root)
        
        # Simulate loading process
        steps = [
            (20, "Loading Database..."),
            (40, "Loading Assets..."),
            (60, "Loading Templates..."),
            (80, "Initializing UI..."),
            (100, "Ready")
        ]
        
        for val, text in steps:
            splash.update_progress(val / 100.0, text)
            time.sleep(0.1) # Simulate real load time securely
            
        splash.destroy()
        
        # Build main app
        from ui.app import KDPStudioApp
        # KDPStudioApp is a CTk instance. We shouldn't have two CTk instances.
        # So we destroy the hidden root, and let KDPStudioApp be the root.
        root.destroy()
        
        app = KDPStudioApp()
        app.mainloop()
    except Exception as e:
        logger.error(f"Application error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
