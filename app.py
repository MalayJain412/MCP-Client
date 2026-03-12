from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from mcp_engine import MCPAgent


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