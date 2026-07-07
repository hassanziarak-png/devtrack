import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.migrate import run_migrations
from app.routers import auth, holidays, leaves, reports, tasks, users
from app.scheduler import run_scheduled_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_scheduled_report, "cron", hour=8, minute=0)
    scheduler.start()
    logger.info("%s started", settings.app_name)
    yield
    scheduler.shutdown()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(users.router)
app.include_router(leaves.router)
app.include_router(holidays.router)
app.include_router(reports.router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
