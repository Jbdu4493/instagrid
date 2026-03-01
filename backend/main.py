import os
import uvicorn
import logging
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from config import logger, APP_PASSWORD
from security.token_manager import TokenManager
from routers import auth, analysis, instagram, drafts, ai_config

API_KEY_NAME = "X-App-Password"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_app_password(api_key_header: str = Depends(api_key_header)):
    if not APP_PASSWORD:
        return True # If no password configured, disabled secure mode
    if api_key_header != APP_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mot de passe de l'application invalide",
        )
    return True

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

@app.get("/verify-password")
def verify_password(is_valid: bool = Depends(verify_app_password)):
    """Endpoint purely to verify the app password from the frontend."""
    return {"status": "ok", "valid": True}

# Include Routers with Security Dependency
app.include_router(auth.router, tags=["auth"], dependencies=[Depends(verify_app_password)])
app.include_router(analysis.router, tags=["analysis"], dependencies=[Depends(verify_app_password)])
app.include_router(instagram.router, tags=["instagram"], dependencies=[Depends(verify_app_password)])
app.include_router(drafts.router, prefix="/drafts", tags=["drafts"], dependencies=[Depends(verify_app_password)])
app.include_router(ai_config.router, tags=["ai_config"], dependencies=[Depends(verify_app_password)])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
