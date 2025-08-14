#!/usr/bin/env python3
"""
Demo script to showcase the Database Chatbot UI
This script starts the API server and opens the web UI automatically
"""

import os
import sys
import time
import webbrowser
import subprocess
from pathlib import Path

def check_requirements():
    """Check if all requirements are met"""
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        print("✅ Core requirements installed")
        return True
    except ImportError as e:
        print(f"❌ Missing requirements: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def check_docker():
    """Check if Docker is available"""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker is available")
            return True
    except FileNotFoundError:
        pass
    
    print("⚠️  Docker not found - you can still run locally")
    return False

def start_local_server():
    """Start the FastAPI server locally"""
    print("🚀 Starting FastAPI server...")
    
    # Change to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Start uvicorn
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ]
    
    return subprocess.Popen(cmd)

def start_docker():
    """Start with Docker Compose"""
    print("🐳 Starting with Docker Compose...")
    
    project_root = Path(__file__).parent
    docker_compose_path = project_root / "docker" / "docker-compose.yml"
    
    cmd = [
        "docker", "compose",
        "-f", str(docker_compose_path),
        "up", "--build", "-d"
    ]
    
    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode == 0

def wait_for_server(url="http://localhost:8000", timeout=60):
    """Wait for the server to be ready"""
    import requests
    
    print(f"⏳ Waiting for server to start at {url}...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print("✅ Server is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(2)
        print(".", end="", flush=True)
    
    print(f"\n❌ Server not ready after {timeout} seconds")
    return False

def open_ui():
    """Open the web UI in the default browser"""
    ui_url = "http://localhost:8000/ui"
    print(f"🌐 Opening web UI: {ui_url}")
    webbrowser.open(ui_url)

def demo_instructions():
    """Print demo instructions"""
    print("\n" + "="*60)
    print("🎯 DEMO READY!")
    print("="*60)
    print("Web UI: http://localhost:8000/ui")
    print("API Docs: http://localhost:8000/docs")
    print("\n📋 DEMO CHECKLIST:")
    print("1. ✅ Connect to Database (use sample credentials)")
    print("2. ✅ Create New Chat Session")
    print("3. ✅ Try Example Queries:")
    print("   - 'Show me all users'")
    print("   - 'How many orders today?'")
    print("   - 'List Engineering users'")
    print("4. ✅ Show Real-time Streaming")
    print("5. ✅ Demonstrate Cache Hits (run same query twice)")
    print("6. ✅ Export Chat Session")
    print("\n🔑 CREDENTIALS (Docker):")
    print("PostgreSQL:")
    print("  Host: localhost, Port: 5432")
    print("  DB: sampledb, User: postgres, Pass: postgres")
    print("\nMongoDB:")
    print("  Host: localhost, Port: 27017")
    print("  DB: sampledb, User: appuser, Pass: apppassword")
    print("\n⚠️  NOTE: Set OPENAI_API_KEY for LLM functionality")
    print("="*60)

def main():
    print("🤖 Database Chatbot Demo Launcher")
    print("="*50)
    
    # Check requirements
    if not check_requirements():
        return
    
    # Check Docker
    has_docker = check_docker()
    
    # Ask user preference
    if has_docker:
        choice = input("\nChoose startup method:\n1. Docker (recommended) \n2. Local Python\nEnter choice (1/2): ").strip()
        use_docker = choice == "1" or choice.lower() == "docker"
    else:
        use_docker = False
        print("\nUsing local Python since Docker is not available")
    
    # Start server
    server_process = None
    try:
        if use_docker:
            if not start_docker():
                print("❌ Failed to start Docker containers")
                return
        else:
            server_process = start_local_server()
        
        # Wait for server
        if wait_for_server():
            # Open UI
            time.sleep(2)
            open_ui()
            
            # Show instructions
            demo_instructions()
            
            # Keep running
            if use_docker:
                print("\n🔄 Containers are running. Press Ctrl+C to stop...")
                try:
                    input("\nPress Enter to stop containers...")
                except KeyboardInterrupt:
                    pass
                print("\n🛑 Stopping containers...")
                subprocess.run(["docker", "compose", "-f", "docker/docker-compose.yml", "down"])
            else:
                print("\n🔄 Server is running. Press Ctrl+C to stop...")
                try:
                    server_process.wait()
                except KeyboardInterrupt:
                    print("\n🛑 Stopping server...")
                    server_process.terminate()
                    server_process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        if server_process:
            server_process.terminate()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
