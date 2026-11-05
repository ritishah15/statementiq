from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

app = FastAPI(
    title="StatementIQ API",
    description="Bank Statement Processing & Non-LLM Classification System",
    version="1.0.0"
)

# Configure CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
async def root():
    return {
        "app": "StatementIQ",
        "status": "online",
        "description": "Bank Statement Processing & Classification System (Non-LLM)"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
