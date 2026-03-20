from fastapi import APIRouter

from app.routes import projects, render

api_router = APIRouter()
api_router.include_router(render.router, tags=["render"])
api_router.include_router(projects.router, tags=["projects"])
