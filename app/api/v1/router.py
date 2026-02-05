from fastapi import APIRouter
from app.api.v1 import honeypot

api_router = APIRouter()

# Include honeypot endpoints
api_router.include_router(
    honeypot.router,
    prefix="/honeypot",
    tags=["Honeypot"]
)
