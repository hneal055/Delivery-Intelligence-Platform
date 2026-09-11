import os
import subprocess
import sys
import shutil

project_dir = r"C:\Projects\DELIVERYINTELLIGENCEPLATFORM\src\mobile"
os.chdir(project_dir)

print("[Agent] Initializing autonomous environment repair...")

# 1. Clear conflicting environment variables
if "NODE_OPTIONS" in os.environ:
    del os.environ["NODE_OPTIONS"]

# 2. Check current node version via subprocess
result = subprocess.run(["node", "-v"], capture_output=True, text=True)
print(f"[Agent] Active Node Version: {result.stdout.strip()}")

# 3. Clean corrupted modules if needed
if not os.path.exists("node_modules") or not os.path.exists("node_modules/expo"):
    print("[Agent] node_modules missing or incomplete. Reinstalling dependencies...")
    subprocess.run(["npm", "install"], check=True)

print("[Agent] Environment prepared successfully. Launching Expo dev server...")

# 4. Run Expo start
try:
    subprocess.run(["npx", "expo", "start", "--localhost", "--clear"], check=True)
except subprocess.CalledProcessError as e:
    print(f"[Agent] Expo failed to start with code {e.returncode}. Attempting fallback wrapper...")
    # Fallback execution using local node runtime if available
    if os.path.exists("node.exe"):
        subprocess.run([r".\node.exe", "node_modules/expo/bin/cli.js", "start", "--localhost", "--clear"])