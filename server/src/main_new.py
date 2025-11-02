"""Hangman Server API - Refactored main application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import repositories
from repositories import UserRepository, SessionRepository, GameRepository, DictionaryRepository

# Import services  
from services.auth_service import AuthService

# Import routes (when ready)
# from routes import api_router, utils_router

# Initialize FastAPI app
app = FastAPI(
    title="Hangman Server API",
    version="1.0.0",
    description="Hangman game server with REST API"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure from settings
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize repositories (singletons)
user_repo = UserRepository()
session_repo = SessionRepository()
game_repo = GameRepository()
dict_repo = DictionaryRepository()

# Initialize services with dependency injection
auth_service = AuthService(user_repo)
# session_service = SessionService(session_repo, dict_repo)
# game_service = GameService(game_repo, session_repo, dict_repo)
# stats_service = StatsService(user_repo, session_repo, game_repo)
# dict_service = DictionaryService(dict_repo)

# Include routers
# app.include_router(api_router)
# app.include_router(utils_router)

# TODO: Import and register all routes from routes/ package
# For now, keeping original endpoints inline until routes are fully implemented

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
