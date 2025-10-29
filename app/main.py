from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import webhook
from app.database import engine, Base
from app.models import WeatherStationData
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)
logger.info("Tablas creadas/verificadas en la base de datos")

app = FastAPI(
    title="Microservicio Meteorológico",
    description="API para recibir datos de estaciones meteorológicas",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "Microservicio funcionando correctamente",
        "database": "PostgreSQL",
        "status": "active",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
