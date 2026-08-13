class VariableRegistry:
    def __init__(self):
        self._global_variables = {
            "BOOK_TITLE": "Untitled Planner",
            "AUTHOR": "Unknown Author",
            "TOTAL_PAGES": "100"
        }
        
    def set_global(self, key: str, value: str):
        self._global_variables[key] = str(value)
        
    def get_globals(self) -> dict:
        return self._global_variables.copy()

# Singleton instance
registry = VariableRegistry()
