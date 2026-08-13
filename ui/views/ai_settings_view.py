import customtkinter as ctk
from tkinter import messagebox

from book_builder.services.ai.manager import AIManager
from book_builder.services.credential_service import ICredentialService
from book_builder.services.ai.models import AIRequest

class AISettingsView(ctk.CTkFrame):
    def __init__(self, master, ai_manager: AIManager, credential_service: ICredentialService, config: dict, **kwargs):
        super().__init__(master, **kwargs)
        self.ai_manager = ai_manager
        self.credential_service = credential_service
        self.config = config
        
        self._build_ui()
        self._load_current_settings()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        
        header = ctk.CTkLabel(self, text="AI Foundation Settings", font=ctk.CTkFont(size=20, weight="bold"))
        header.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))

        # Enable AI Toggle
        self.ai_enabled_var = ctk.BooleanVar(value=False)
        self.enable_switch = ctk.CTkSwitch(
            self, text="Enable AI Features", variable=self.ai_enabled_var, 
            command=self._on_enable_toggle
        )
        self.enable_switch.grid(row=1, column=0, sticky="w", padx=20, pady=10)

        # Provider Settings Frame
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        self.settings_frame.grid_columnconfigure(1, weight=1)

        # Provider
        ctk.CTkLabel(self.settings_frame, text="AI Provider:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.provider_combo = ctk.CTkComboBox(
            self.settings_frame, values=["openai", "mock", "none"], command=self._on_provider_change
        )
        self.provider_combo.grid(row=0, column=1, sticky="ew", padx=10, pady=10)

        # Model
        ctk.CTkLabel(self.settings_frame, text="Model Name:").grid(row=1, column=0, sticky="w", padx=10, pady=10)
        self.model_entry = ctk.CTkEntry(self.settings_frame, placeholder_text="e.g., gpt-4o-mini")
        self.model_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=10)

        # API Key
        ctk.CTkLabel(self.settings_frame, text="API Key:").grid(row=2, column=0, sticky="w", padx=10, pady=10)
        self.api_key_entry = ctk.CTkEntry(self.settings_frame, show="*", placeholder_text="Enter API Key (saved securely)")
        self.api_key_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=10)

        # Buttons
        button_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        button_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=20)
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        self.save_btn = ctk.CTkButton(button_frame, text="Save Settings", command=self._save_settings)
        self.save_btn.grid(row=0, column=0, padx=10)

        self.test_btn = ctk.CTkButton(button_frame, text="Test Connection", command=self._test_connection, fg_color="gray")
        self.test_btn.grid(row=0, column=1, padx=10)

    def _load_current_settings(self):
        ai_config = self.config.get("ai_settings", {})
        provider = ai_config.get("provider", "none")
        model = ai_config.get("model", "gpt-4o-mini")
        is_enabled = ai_config.get("enabled", False)

        self.ai_enabled_var.set(is_enabled)
        self.provider_combo.set(provider)
        self.model_entry.insert(0, model)
        
        self._on_enable_toggle()
        self._on_provider_change(provider)

    def _on_enable_toggle(self):
        state = "normal" if self.ai_enabled_var.get() else "disabled"
        self.provider_combo.configure(state=state)
        self.model_entry.configure(state=state)
        self.api_key_entry.configure(state=state)
        self.save_btn.configure(state=state)
        self.test_btn.configure(state=state)

    def _on_provider_change(self, value):
        if value in ("mock", "none"):
            self.api_key_entry.configure(state="disabled")
        elif self.ai_enabled_var.get():
            self.api_key_entry.configure(state="normal")
            
            # Load existing key silently
            existing_key = self.credential_service.get_credential("kdp_studio_ai", value)
            self.api_key_entry.delete(0, "end")
            if existing_key:
                # Provide visual feedback that a key is stored without showing it
                self.api_key_entry.insert(0, "********")

    def _save_settings(self):
        provider = self.provider_combo.get()
        model = self.model_entry.get().strip()
        is_enabled = self.ai_enabled_var.get()
        
        api_key = self.api_key_entry.get().strip()

        if is_enabled and provider not in ("mock", "none") and api_key and api_key != "********":
            success = self.credential_service.set_credential("kdp_studio_ai", provider, api_key)
            if not success:
                messagebox.showerror("Security Error", "Failed to securely save API key to OS Keyring.")
                return

        # Update global config 
        if hasattr(self.config, "set"):
            self.config.set("ai_settings", {
                "provider": provider,
                "model": model,
                "enabled": is_enabled
            })
        else:
            self.config["ai_settings"] = {
                "provider": provider,
                "model": model,
                "enabled": is_enabled
            }

        # Reconfigure live manager
        if is_enabled:
            success = self.ai_manager.configure(provider, model_name=model)
            if success:
                messagebox.showinfo("Success", "AI settings saved successfully.")
            else:
                messagebox.showerror("Error", "Failed to configure AIManager. Check logs.")
        else:
            self.ai_manager.disable()
            messagebox.showinfo("Success", "AI features disabled successfully.")

    def _test_connection(self):
        if not self.ai_manager.is_enabled:
            messagebox.showwarning("Warning", "Enable and save AI settings before testing.")
            return

        self.test_btn.configure(text="Testing...", state="disabled")
        self.update()

        try:
            req = AIRequest(prompt="Say 'Connection successful'", max_tokens=10)
            res = self.ai_manager.generate_text(req)
            if res.success:
                messagebox.showinfo("Connection Test", f"Success!\nProvider replied: {res.content}")
            else:
                messagebox.showerror("Connection Test Failed", res.error_message)
        finally:
            self.test_btn.configure(text="Test Connection", state="normal")
