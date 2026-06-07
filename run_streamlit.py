import os
import subprocess
import sys

def main():
    # Read the PORT environment variable set by Render (default to 8501 if not found)
    port = os.environ.get("PORT", "8501")
    
    # Construct the streamlit command
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.port",
        port,
        "--server.address",
        "0.0.0.0",
        "--browser.gatherUsageStats",
        "false"
    ]
    
    print(f"Starting Streamlit on port {port}...")
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
