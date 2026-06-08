from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from pydantic import BaseModel

from . import __version__
from .errors import install_error_handlers
from .middleware import install_middleware
from .routers import auth, boundary, codes, collab, exports, jobs, plans, program, projects
from .settings import settings

app = FastAPI(
    title="Floor Plan Studio API",
    version=__version__,
    description="API gateway for the Generative 3D Floor Plan Studio.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

install_middleware(app)
install_error_handlers(app)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(boundary.router)
app.include_router(program.router)
app.include_router(plans.router)
app.include_router(jobs.router)
app.include_router(codes.router)
app.include_router(exports.router)
app.include_router(collab.router)

app.mount("/metrics", make_asgi_app())


class HealthResponse(BaseModel):
    status: str
    service: str


class VersionResponse(BaseModel):
    service: str
    version: str


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name)


@app.get("/version", response_model=VersionResponse, tags=["meta"])
async def version() -> VersionResponse:
    return VersionResponse(service=settings.service_name, version=__version__)
