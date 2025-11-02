"""API routes package."""

from fastapi import APIRouter

# Import individual routers
from . import auth
from . import sessions  
from . import games
from . import stats
from . import admin
from . import utils

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(games.router, tags=["Games"])
api_router.include_router(stats.router, tags=["Statistics"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])

# Utility routes (health, version, time)
utils_router = utils.router

__all__ = ["api_router", "utils_router"]
