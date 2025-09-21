#!/usr/bin/env python3
"""
Emergence Simulator Directory Cleanup Script
Cleans up project structure, removes unnecessary files, and organizes everything properly.
"""

import os
import shutil
import glob
from pathlib import Path
import sys

class ProjectCleanup:
    def __init__(self, root_dir="."):
        self.root = Path(root_dir).resolve()
        self.changes_made = []
        
    def log(self, action, detail=""):
        message = f"✅ {action}"
        if detail:
            message += f": {detail}"
        print(message)
        self.changes_made.append(message)
    
    def warn(self, message):
        print(f"⚠️  {message}")
    
    def error(self, message):
        print(f"❌ {message}")
    
    def remove_pycache(self):
        """Remove all __pycache__ directories and .pyc files"""
        print("🧹 Cleaning Python cache files...")
        
        # Find and remove __pycache__ directories
        pycache_dirs = list(self.root.rglob("__pycache__"))
        for pycache_dir in pycache_dirs:
            if pycache_dir.is_dir():
                shutil.rmtree(pycache_dir)
                self.log("Removed __pycache__", str(pycache_dir.relative_to(self.root)))
        
        # Find and remove .pyc files
        pyc_files = list(self.root.rglob("*.pyc"))
        for pyc_file in pyc_files:
            pyc_file.unlink()
            self.log("Removed .pyc file", str(pyc_file.relative_to(self.root)))
    
    def remove_temp_files(self):
        """Remove temporary and backup files"""
        print("🧹 Cleaning temporary files...")
        
        temp_patterns = [
            "*.tmp", "*.temp", "*.bak", "*.swp", "*.swo",
            "*~", "*.orig", ".DS_Store", "Thumbs.db"
        ]
        
        for pattern in temp_patterns:
            files = list(self.root.rglob(pattern))
            for file in files:
                file.unlink()
                self.log("Removed temp file", str(file.relative_to(self.root)))
    
    def organize_requirements(self):
        """Clean up requirements files"""
        print("📦 Organizing requirements files...")
        
        req_files = ["requirements-minimal.txt", "requirements-simple.txt"]
        
        for req_file in req_files:
            file_path = self.root / req_file
            if file_path.exists():
                file_path.unlink()
                self.log("Removed duplicate requirements", req_file)
        
        # Ensure main requirements.txt is clean
        req_path = self.root / "requirements.txt"
        if req_path.exists():
            self.log("Kept main requirements.txt")
    
    def remove_old_launchers(self):
        """Remove old launcher versions"""
        print("🚀 Cleaning launcher files...")
        
        old_launchers = ["launcher-simple.sh"]
        for launcher in old_launchers:
            file_path = self.root / launcher
            if file_path.exists():
                file_path.unlink()
                self.log("Removed old launcher", launcher)
    
    def create_missing_directories(self):
        """Ensure all required directories exist"""
        print("📁 Creating required directories...")
        
        required_dirs = [
            "results",
            "logs", 
            "test-results",
            "storage/migrations",
            "simulations/templates",
            "web/static/css",
            "web/static/js",
            "web/static/images"
        ]
        
        for dir_path in required_dirs:
            full_path = self.root / dir_path
            if not full_path.exists():
                full_path.mkdir(parents=True, exist_ok=True)
                self.log("Created directory", dir_path)
    
    def create_missing_init_files(self):
        """Ensure all Python packages have __init__.py files"""
        print("🐍 Creating missing __init__.py files...")
        
        python_dirs = [
            "api/routes",
            "tests/unit", 
            "tests/integration",
            "tests/e2e",
            "web/static",
            "simulations/templates"
        ]
        
        for dir_path in python_dirs:
            full_path = self.root / dir_path
            if full_path.exists() and not (full_path / "__init__.py").exists():
                (full_path / "__init__.py").touch()
                self.log("Created __init__.py", f"{dir_path}/__init__.py")
    
    def create_gitignore(self):
        """Create comprehensive .gitignore"""
        print("📝 Creating .gitignore...")
        
        gitignore_content = """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/
.venv/

# Environment files
.env
.env.local
.env.production

# IDE files
.vscode/
.idea/
*.swp
*.swo
*~

# OS files
.DS_Store
Thumbs.db

# Logs
logs/
*.log

# Test results
test-results/
htmlcov/
.coverage
.pytest_cache/

# Results and data
results/
data/
*.db
*.sqlite

# Temporary files
*.tmp
*.temp
*.bak
*.orig

# Node modules (if any)
node_modules/

# Jupyter notebooks
.ipynb_checkpoints/

# Redis
dump.rdb
"""
        
        gitignore_path = self.root / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text(gitignore_content)
            self.log("Created .gitignore")
        else:
            self.log("Found existing .gitignore")
    
    def create_missing_templates(self):
        """Create missing web templates"""
        print("🌐 Checking web templates...")
        
        templates_dir = self.root / "web/templates"
        templates_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
        required_templates = ["compare.html", "shared.html", "embed.html", "error.html"]
        
        for template in required_templates:
            template_path = templates_dir / template
            if not template_path.exists():
                # Create basic template
                basic_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{template.replace('.html', '').title()} - Emergence Simulator</title>
    <style>
        body {{ font-family: system-ui, sans-serif; margin: 40px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{template.replace('.html', '').title()}</h1>
        <p>This page is under construction.</p>
        <a href="/">&larr; Back to Home</a>
    </div>
</body>
</html>"""
                template_path.write_text(basic_content)
                self.log("Created template", template)
    
    def organize_static_files(self):
        """Organize static web files"""
        print("🎨 Organizing static files...")
        
        static_dir = self.root / "web/static"
        
        # Create CSS directory and basic styles
        css_dir = static_dir / "css"
        css_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
        if not (css_dir / "main.css").exists():
            basic_css = """/* Emergence Simulator Styles */
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    margin: 0;
    padding: 0;
    background: #f5f5f5;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.btn {
    display: inline-block;
    padding: 10px 20px;
    background: #007bff;
    color: white;
    text-decoration: none;
    border-radius: 4px;
    border: none;
    cursor: pointer;
}

.btn:hover {
    background: #0056b3;
}
"""
            (css_dir / "main.css").write_text(basic_css)
            self.log("Created main.css")
    
    def validate_structure(self):
        """Validate the final project structure"""
        print("🔍 Validating project structure...")
        
        required_files = [
            "README.md",
            "requirements.txt", 
            "main.py",
            "launcher.sh",
            "training.sh",
            "test.sh",
            ".env.example" if not (self.root / ".env").exists() else ".env"
        ]
        
        for file in required_files:
            file_path = self.root / file
            if file_path.exists():
                self.log("Validated file", file)
            else:
                self.warn(f"Missing required file: {file}")
    
    def create_env_example(self):
        """Create .env.example if missing"""
        env_example_path = self.root / ".env.example"
        if not env_example_path.exists():
            env_content = """DATABASE_URL=postgresql://user:pass@localhost/emergence
OPENROUTER_API_KEY=your_openrouter_api_key_here
DEFAULT_MODEL=meta-llama/llama-3-70b-instruct
SECRET_KEY=your_secret_key_here
BASE_URL=http://localhost:5000
REDIS_URL=redis://localhost:6379/0
"""
            env_example_path.write_text(env_content)
            self.log("Created .env.example")
    
    def run_cleanup(self):
        """Run full cleanup process"""
        print("🧹 Starting Emergence Simulator cleanup...")
        print(f"📁 Working directory: {self.root}")
        print()
        
        # Cleanup tasks
        self.remove_pycache()
        self.remove_temp_files() 
        self.organize_requirements()
        self.remove_old_launchers()
        self.create_missing_directories()
        self.create_missing_init_files()
        self.create_gitignore()
        self.create_env_example()
        self.create_missing_templates()
        self.organize_static_files()
        self.validate_structure()
        
        # Summary
        print()
        print("🎉 Cleanup completed!")
        print(f"📊 Total changes made: {len(self.changes_made)}")
        print()
        print("✨ Your Emergence Simulator is now perfectly organized!")
        print()
        
        # Final structure check
        print("📁 Final project structure:")
        os.system("tree -I 'venv|__pycache__|*.pyc' -L 3")

if __name__ == "__main__":
    cleanup = ProjectCleanup()
    cleanup.run_cleanup()