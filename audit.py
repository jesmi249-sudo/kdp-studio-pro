import os
import ast

def check_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            content = f.read()
            tree = ast.parse(content)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return
            
    # Very basic static analysis
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                print(f"{filepath}:{node.lineno} - Bare except found (consider catching Exception as e)")

def main():
    for root, dirs, files in os.walk('.'):
        if '.venv' in root or '.git' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                check_file(os.path.join(root, file))

if __name__ == '__main__':
    main()
