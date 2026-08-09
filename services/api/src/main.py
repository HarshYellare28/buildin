from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import demo, health, people, plans

app = FastAPI(title="DAWA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(people.router)
app.include_router(demo.router)
app.include_router(plans.router)
