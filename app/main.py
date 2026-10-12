from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import BASE_DIR, STORAGE_DIR, CERTS_DIR
from app.database import init_db
from app.routers import auth, files, editor, transfer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure directories and database tables exist
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    yield
    # Shutdown logic if any

app = FastAPI(
    title="Webapp File Server",
    description="Secure, Mobile and Desktop-Friendly HTTPS File Management Web Server",
    version="1.0.0",
    lifespan=lifespan
)

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

# Security and CORS Middleware
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# Mount Static Assets
static_dir = BASE_DIR / "app" / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount API Routers
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(editor.router)
app.include_router(transfer.router)

# Template Page Routes
templates_dir = BASE_DIR / "app" / "templates"

@app.get("/", response_class=FileResponse)
async def serve_index():
    return FileResponse(templates_dir / "index.html")

@app.get("/login", response_class=FileResponse)
async def serve_login():
    return FileResponse(templates_dir / "login.html")

@app.get("/setup", response_class=FileResponse)
async def serve_setup():
    return FileResponse(templates_dir / "setup.html")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "webapp-file-server"}
