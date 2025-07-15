import subprocess
import os
import threading
import time
import sys
import webbrowser

def run_backend():

    try:
        from backend.api import start_server
        start_server(host="127.0.0.1", port=8000)
    except Exception as e:
        pass

def run_frontend():
    os.environ["CATBOT_ROOT"] = os.path.dirname(os.path.abspath(__file__))
    cmd = [sys.executable, "-m", "streamlit", "run", "frontend/app.py", "--server.port=8501", "--server.address=127.0.0.1"]
    subprocess.Popen(cmd)

def main():
    # Start the backend in a separate thread
    backend_thread = threading.Thread(target=run_backend)
    backend_thread.daemon = True
    backend_thread.start()
    
    time.sleep(2)
    
    run_frontend()
    
    webbrowser.open("http://localhost:8501")
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    main() 