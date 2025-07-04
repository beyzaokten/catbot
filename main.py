import subprocess
import os
import threading
import time
import sys
import webbrowser
import requests

def run_backend():
    print("Starting backend server...")
    try:
        from backend.api import start_server
        start_server(host="127.0.0.1", port=8000)
    except Exception as e:
        print(f"Error starting backend server: {str(e)}")

def run_frontend():
    print("Starting frontend...")
    os.environ["CATBOT_ROOT"] = os.path.dirname(os.path.abspath(__file__))
    cmd = [sys.executable, "-m", "streamlit", "run", "frontend/app.py", "--server.port=8501", "--server.address=127.0.0.1"]
    subprocess.Popen(cmd)

def check_ollama_running():
    """Check if Ollama is running"""
    try:
        print("Checking if Ollama is running...")
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            print("Ollama is running")
            return True
        else:
            print(f"Ollama returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error checking Ollama: {str(e)}")
        return False

def main():
    print("Starting CatBot application...")
    
    try:
        import ollama
        print("Ollama Python package is installed.")
        
        if check_ollama_running():
            print("Ollama service is running.")
            print("Checking for llama3 model...")
            try:
                response = requests.get("http://localhost:11434/api/tags")
                models = response.json().get("models", [])
                model_names = [model.get("name", "") for model in models]
                
                # Check if any model name contains "llama3"
                llama3_found = any("llama3" in name for name in model_names)
                
                if llama3_found:
                    llama3_models = [name for name in model_names if "llama3" in name]
                    print(f"llama3 model is available: {', '.join(llama3_models)}")
                else:
                    print("llama3 model not found. Please run: 'ollama pull llama3'")
                    print(f"Available models: {', '.join(model_names) if model_names else 'None'}")
            except Exception as e:
                print(f"Error checking models: {e}")
        else:
            print("Ollama service is not running. Please start Ollama.")
            print("Visit https://ollama.com/download for installation instructions.")
    except ImportError:
        print("Ollama Python package not found.")
        print("Please make sure Ollama is installed and running on your system.")
        print("Visit https://ollama.com/download for installation instructions.")
        
    # Start the backend in a separate thread
    backend_thread = threading.Thread(target=run_backend)
    backend_thread.daemon = True
    backend_thread.start()
    
    time.sleep(2)
    
    run_frontend()
    
    webbrowser.open("http://localhost:8501")
    
    print("CatBot is running!")
    print("Backend API: http://127.0.0.1:8000")
    print("Frontend UI: http://127.0.0.1:8501")
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down CatBot...")
        sys.exit(0)

if __name__ == "__main__":
    main() 