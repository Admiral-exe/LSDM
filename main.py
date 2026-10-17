"""
Main Application Entry Point.
Starts the FastAPI application and PyWebView Desktop Window.
"""
import sys
import threading
import time
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

import config
import version
from backend.database import init_db, get_config_val
from backend.excel_reader import ExcelReader
from backend.routes.arrival_routes import router as arrival_router
from backend.routes.dispatch_routes import router as dispatch_router
from backend.routes.tally_routes import router as tally_router
from backend.routes.directory_routes import router as directory_router

# Initialize FastAPI App
app = FastAPI(title="Supply Chain & Laboratory Sample Management System")

# Active WebSocket Connections
connected_clients: list[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

async def broadcast_ws(event: str, data: dict = None):
    """Broadcasts state changes to all open UI instances."""
    msg = {"event": event, "data": data or {}}
    for client in list(connected_clients):
        try:
            await client.send_json(msg)
        except Exception:
            if client in connected_clients:
                connected_clients.remove(client)

# Register API Routers
app.include_router(arrival_router)
app.include_router(dispatch_router)
app.include_router(tally_router)
app.include_router(directory_router)

# Mount Static Frontend
frontend_dir = config.get_resource_path("frontend")
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

@app.get("/")
def serve_index():
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Frontend not yet generated."}

@app.get("/api/version")
def api_version():
    """Returns application version metadata."""
    return version.get_version_info()

def start_server():
    """Runs Uvicorn web server."""
    uvicorn.run(
        app,
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        log_level="warning"
    )

def main():
    print("=" * 70)
    print(" Supply Chain & Laboratory Sample Management Desktop System")
    print("=" * 70)

    # 1. Initialize SQLite Database (WAL Mode)
    print("[1/3] Initializing SQLite database...")
    init_db()

    # 2. Ingest Existing Workspace Files
    ws_folder = get_config_val("workspace_folder_path", str(config.BASE_DIR))
    print(f"[2/3] Scanning workspace directory '{ws_folder}'...")
    scan_res = ExcelReader.full_scan_workspace(ws_folder)
    print(f"      Scan Completed: {scan_res}")

    # 3. Start Server Thread
    print(f"[3/3] Starting backend server at http://{config.SERVER_HOST}:{config.SERVER_PORT}...")
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Allow server to bind
    time.sleep(1.2)

    # Check command-line flag for headless mode
    if "--headless" in sys.argv or "--server-only" in sys.argv:
        print(f"\nRunning in server mode. Open http://{config.SERVER_HOST}:{config.SERVER_PORT} in your browser.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down server.")
            sys.exit(0)
    else:
        # Launch PyWebView Native Desktop Window
        try:
            import webview
            print("\nLaunching Desktop Window...")
            window = webview.create_window(
                title=f"LSDM v{version.__version__} - Laboratory Sample & Supply Management System",
                url=f"http://{config.SERVER_HOST}:{config.SERVER_PORT}",
                width=1440,
                height=900,
                min_size=(1200, 750),
                background_color="#1b1e24"
            )
            webview.start()
        except Exception as e:
            print(f"\n[Notice] Could not initialize native PyWebView ({e}). Falling back to browser server mode.")
            print(f"Access the system at: http://{config.SERVER_HOST}:{config.SERVER_PORT}")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                sys.exit(0)

if __name__ == "__main__":
    main()
