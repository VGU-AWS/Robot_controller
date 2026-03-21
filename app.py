from fastapi import FastAPI
from enum import Enum

app = FastAPI()

class StatusCode(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DISCONNECTED = "disconnected"

class Robot():
    def __init__(self, robot_id: str, status: StatusCode):
        self.robot_id = robot_id
        self.status = status
    def move(self, direction: str):
        return f"Robot {self.robot_id} is moving {direction}"

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/handshake/{client_id}")
async def handshake(client_id: str):
    return {"message": f"Handshake successful for client {client_id}"}

@app.get("/receive_command/{client_id}")
async def receive_command(client_id: str):
    return {"message": f"Data received for client {client_id}"}


@app.get("/send_command/{client_id}")
async def send_command(client_id: str):
    return {"message": f"Command sent to client {client_id}"}

@app.get("/check_status/")
async def check_status():
    return {"message": "Status check successful"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)

