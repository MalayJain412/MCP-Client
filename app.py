from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from mcp_engine import MCPAgent

from pathlib import Path

import ast

from config import ADMIN_TOKEN

import subprocess

SERVER_FILE = Path("servers.py")

admin_token = ADMIN_TOKEN

# -------------------------------
# FastAPI app
# -------------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------
# Request / Response models
# -------------------------------

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class ServerFileUpdate(BaseModel):
    content: str

# -------------------------------
# Admin verification
# -------------------------------

def verify_admin(token: str | None):
    if token != admin_token:
        raise HTTPException(status_code=403, detail="Unauthorized")

# -------------------------------
# Global agent instance
# -------------------------------

agent = MCPAgent()


# -------------------------------
# Startup initialization
# -------------------------------

@app.on_event("startup")
async def startup_event():

    await agent.initialize()


# -------------------------------
# Chat endpoint
# -------------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):

    result = await agent.run(req.message)

    return {"reply": result}


# -------------------------------
# Read server file
# -------------------------------

@app.get("/admin/server-file")
async def get_server_file(x_admin_token: str | None = Header(default=None)):
    
    verify_admin(x_admin_token)
    
    try:
        content = SERVER_FILE.read_text()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# -------------------------------
# Update server file
# -------------------------------

@app.post("/admin/server-file")
async def update_server_file(data: ServerFileUpdate, x_admin_token: str | None = Header(default=None)):
    
    verify_admin(x_admin_token)
    
    try:
        ast.parse(data.content)
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Invalid Python syntax: {e}")
    
    try:
        SERVER_FILE.write_text(data.content)
        
        # restart backend using pm2
        subprocess.Popen(["pm2", "restart", "mcp-client"])
        
        return {
            "status": "updated",
            "message": "Server file updated. Restart triggered."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))