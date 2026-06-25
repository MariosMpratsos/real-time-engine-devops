from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import random
import math
import time
import json
import uvicorn
import sqlite3
from contextlib import asynccontextmanager

# --- Ρυθμίσεις Βάσης Δεδομένων ---
# Ανοίγουμε σύνδεση με την SQLite (φτιάχνει το αρχείο metrics.db αν δεν υπάρχει)
conn = sqlite3.connect("metrics.db", check_same_thread=False)
cursor = conn.cursor()

def init_db():
    """Δημιουργεί τον πίνακα αν τρέχουμε το script για πρώτη φορά"""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER,
            cpu_usage REAL,
            memory_usage REAL,
            active_users INTEGER
        )
    ''')
    conn.commit()

# --- Διαχειριστής WebSockets ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print("❌ Client disconnected.")

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

# --- Data Simulator & Database Writer ---
async def data_generator():
    """Παράγει metrics, τα στέλνει στο React ΚΑΙ τα σώζει στη Βάση"""
    while True:
        current_time = time.time()
        
        # 1. Δημιουργία των Data
        data = {
            "timestamp": int(current_time * 1000),
            "cpu_usage": round(50 + 40 * math.sin(current_time) + random.uniform(-5, 5), 2),
            "memory_usage": round(random.uniform(60, 85), 2),
            "active_users": int(1000 + random.uniform(-50, 50))
        }
        
        # 2. Αποθήκευση στη Βάση Δεδομένων (The Backend Move)
        cursor.execute('''
            INSERT INTO system_metrics (timestamp, cpu_usage, memory_usage, active_users)
            VALUES (?, ?, ?, ?)
        ''', (data["timestamp"], data["cpu_usage"], data["memory_usage"], data["active_users"]))
        conn.commit()
        
        # 3. Αποστολή στους Clients
        if manager.active_connections:
            await manager.broadcast(json.dumps(data))
            
        await asyncio.sleep(0.1)

# --- Lifespan & FastAPI Setup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Initializing Database...")
    init_db()
    print("🚀 Starting Data Engine...")
    task = asyncio.create_task(data_generator())
    yield
    print("🛑 Stopping Engine & Closing DB...")
    task.cancel()
    conn.close()

app = FastAPI(title="Real-Time Engine API", lifespan=lifespan)

# --- Endpoints ---
@app.websocket("/ws/metrics")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ΝΕΟ API ENDPOINT: Για να ζητάει το React το ιστορικό!
@app.get("/api/history")
def get_history():
    """Επιστρέφει τις τελευταίες 50 εγγραφές από τη βάση"""
    cursor.execute("SELECT timestamp, cpu_usage, memory_usage, active_users FROM system_metrics ORDER BY timestamp DESC LIMIT 50")
    rows = cursor.fetchall()
    
    # Τα επιστρέφουμε με τη σωστή σειρά (από το παλιότερο στο νεότερο)
    history = [
        {"timestamp": row[0], "cpu_usage": row[1], "memory_usage": row[2], "active_users": row[3]}
        for row in reversed(rows)
    ]
    return history

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
