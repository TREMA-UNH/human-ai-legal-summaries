#!/usr/bin/env python3
"""
Install all required dependencies for NextPoint
"""
import subprocess
import sys

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"Installing {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing {description}: {e}")
        print(f"Command output: {e.stdout}")
        print(f"Command error: {e.stderr}")
        return False

def main():
    """Install all dependencies"""
    print("Installing NextPoint dependencies...\n")
    
    dependencies = [
        ("pip install -e .", "NextPoint package"),
        ("pip install boto3 botocore", "AWS SDK"),
        ("pip install pydantic tenacity", "Core utilities"),
        ("pip install fastapi uvicorn", "Web framework"),
        ("pip install python-multipart", "File upload support"),
        ("pip install spacy", "NLP library"),
    ]
    
    success_count = 0
    for command, description in dependencies:
        if run_command(command, description):
            success_count += 1
        print()
    
    print(f"Installation complete: {success_count}/{len(dependencies)} packages installed successfully")
    
    if success_count == len(dependencies):
        print("\n🎉 All dependencies installed! You can now run:")
        print("   python3 -m uvicorn backend.nugget_gen_eval:app --reload --port 8000")
    else:
        print(f"\n⚠️  Some dependencies failed to install. Please install them manually.")

if __name__ == "__main__":
    main()