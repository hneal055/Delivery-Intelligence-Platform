import os
import subprocess
import sys

project_dir = r"C:\Projects\DELIVERYINTELLIGENCEPLATFORM\src\mobile"
os.chdir(project_dir)

print("[Agent] Initializing autonomous environment repair...")

if "NODE_OPTIONS" in os.environ:
    del os.environ["NODE_OPTIONS"]

result = subprocess.run(["node", "-v"], capture_output=True, text=True, shell=True)
print(f"[Agent] Active Node Version: {result.stdout.strip()}")

if not os.path.exists("node_modules") or not os.path.exists("node_modules/expo"):
    print("[Agent] node_modules missing or incomplete. Reinstalling dependencies...")
    subprocess.run(["npm", "install"], check=True, shell=True)

print("[Agent] Environment prepared successfully. Launching Expo dev server...")

try:
    subprocess.run(["npx", "expo", "start", "--localhost", "--clear"], check=True, shell=True)
except subprocess.CalledProcessError as e:
    print(f"[Agent] Fallback execution...")
    if os.path.exists("node.exe"):
        subprocess.run([r".\node.exe", "node_modules/expo/bin/cli.js", "start", "--localhost", "--clear"], shell=True)
