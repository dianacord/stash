import os
from pathlib import Path

def should_include(path):
    """Only include Python and important files"""
    extensions = {'.py', '.html', '.css', '.js'}
    exclude_dirs = {'__init__.py','__pycache__', '.pytest_cache', 'htmlcov', '.git', 'venv'}
    
    # Check if any excluded dir is in path
    for exclude in exclude_dirs:
        if exclude in path.parts:
            return False
    
    return path.suffix in extensions

def export_codebase():
    output = []
    root = Path('.')
    
    # Get all files
    files = sorted([f for f in root.rglob('*') if f.is_file() and should_include(f)])
    
    for file_path in files:
        output.append(f"\n{'='*60}\n")
        output.append(f"FILE: {file_path}\n")
        output.append(f"{'='*60}\n\n")
        
        try:
            content = file_path.read_text(encoding='utf-8')
            output.append(content)
        except Exception as e:
            output.append(f"[Error reading file: {e}]")
        
        output.append("\n\n")
    
    # Write to file
    output_file = Path('CODEBASE_EXPORT.txt')
    output_file.write_text(''.join(output), encoding='utf-8')
    print(f"✅ Exported {len(files)} files to {output_file}")

if __name__ == "__main__":
    export_codebase()