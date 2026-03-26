from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from enum import Enum
import boto3

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

runtime = boto3.client("sagemaker-runtime")
ENDPOINT_NAME = os.environ["SAGEMAKER_ENDPOINT_NAME"]

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
    
@app.post("/infer")
async def infer(request: Request):
    body = await request.body()
    content_type = request.headers.get("content-type", "application/octet-stream")

    resp = runtime.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        Body=body,
        ContentType=content_type,
        Accept="application/json",
    )

    result = resp["Body"].read()
    response_content_type = resp.get("ContentType", "application/json")

    return Response(content=result, media_type=response_content_type)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8080")),
    )
