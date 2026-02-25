import os
import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from config import logger
from security.token_manager import TokenManager
from routers import auth, analysis, instagram, drafts

app = FastAPI(title="InstaGrid AI Backend")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc)},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load specific saved token to memory
loaded = TokenManager.load_saved_token()
if loaded:
    pass # Placeholder for potential future logging or action

# --- Endpoints ---
@app.get("/")
def read_root():
    return {"status": "ok", "message": "InstaGrid AI Backend is running"}

@app.get("/config")
def get_config():
    """Expose environment variables to frontend for auto-fill."""
    return {
        "ig_user_id": os.getenv("IG_USER_ID", ""),
        "ig_access_token": os.getenv("IG_ACCESS_TOKEN", ""),
        "fb_app_configured": bool(os.getenv("FB_APP_ID") and os.getenv("FB_APP_SECRET")),
    }

# Include Routers
app.include_router(auth.router, tags=["auth"])
app.include_router(analysis.router, tags=["analysis"])
app.include_router(instagram.router, tags=["instagram"])
app.include_router(drafts.router, prefix="/drafts", tags=["drafts"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
