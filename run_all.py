import sys
import os
import subprocess
import time

def main():
    print("=" * 70)
    print("      AI-Powered Resume Screening & Candidate-Job Matching System     ")
    print("=" * 70)
    
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(workspace_dir, "backend")
    frontend_dir = os.path.join(workspace_dir, "frontend")
    
    # Path to Python in virtual environment
    if sys.platform == "win32":
        python_executable = os.path.join(backend_dir, "venv", "Scripts", "python.exe")
        npm_cmd = "npm.cmd"
    else:
        python_executable = os.path.join(backend_dir, "venv", "bin", "python")
        npm_cmd = "npm"
        
    if not os.path.exists(python_executable):
        python_executable = sys.executable

    print("\n[1/2] Starting FastAPI Backend Server (Port 8000)...")
    backend_process = subprocess.Popen(
        [python_executable, "-m", "uvicorn", "app.main:app", "--port", "8000", "--reload"],
        cwd=backend_dir
    )

    print("[2/2] Starting Vite React Frontend Server (Port 5173)...")
    frontend_process = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=frontend_dir,
        shell=(sys.platform == "win32")
    )

    print("\n" + "-" * 70)
    print("  🚀 Both servers are up and running!")
    print("  ► Frontend Dashboard : http://localhost:5173")
    print("  ► Backend REST API   : http://127.0.0.1:8000")
    print("  ► LM Studio Status   : http://127.0.0.1:8000/ (LM Studio at http://localhost:1234/v1)")
    print("-" * 70)
    print("  Press Ctrl+C to stop both servers cleanly.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping servers...")
        backend_process.terminate()
        frontend_process.terminate()
        print("Done. Goodbye!")

if __name__ == "__main__":
    main()
