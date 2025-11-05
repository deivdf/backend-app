from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from app.database import Base
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class WeatherStationData(Base):
    """
    Tabla para almacenar datos de estaciones meteorológicas
    """

    __tablename__ = "weather_station_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    station_time = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(String(100), nullable=False, index=True)

    temperature = Column(Float, nullable=True)
    precipitation = Column(Float, nullable=True)
    real_precipitation = Column(Float, nullable=True)
    presure = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    wind_direction = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    radiation = Column(Float, nullable=True)
    eto = Column(Float, nullable=True)
    compass_rose = Column(String(10), nullable=True)
    real_eto = Column(Float, nullable=True)
    radiation_uv = Column(Float, nullable=True)
    processed = Column(Integer, default=0, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<WeatherStationData(id={self.id}, source={self.source}, station_time={self.station_time})>"


class DataReceived(BaseModel):
    """
    Modelo para validar datos recibidos del servidor externo
    """

    stationTime: datetime
    temperature: Optional[float] = None
    precipitation: Optional[float] = None
    realPrecipitation: Optional[float] = None
    presure: Optional[float] = None
    windSpeed: Optional[float] = None
    windDirection: Optional[float] = None
    humidity: Optional[float] = None
    radiation: Optional[float] = None
    eto: Optional[float] = None
    compassRose: Optional[str] = None
    realETO: Optional[float] = None
    radiationUV: Optional[float] = None
    source: str

    class Config:
        json_schema_extra = {
            "example": {
                "stationTime": "2023-10-27T10:00:00Z",
                "temperature": 25.5,
                "precipitation": 0.0,
                "realPrecipitation": 0.0,
                "presure": 1012.5,
                "windSpeed": 10.2,
                "windDirection": 180.0,
                "humidity": 60.0,
                "radiation": 500.0,
                "eto": 0.2,
                "compassRose": "S",
                "realETO": 0.21,
                "radiationUV": 5.0,
                "source": "sensor_001",
            }
        }


class DataResponse(BaseModel):
    """
    Respuesta estándar para operaciones
    """

    success: bool
    message: str
    id: Optional[int] = None


class WeatherDataOut(BaseModel):
    """
    Modelo para devolver datos a Flutter
    """

    id: int
    station_time: datetime
    source: str
    temperature: Optional[float] = None
    precipitation: Optional[float] = None
    real_precipitation: Optional[float] = None
    presure: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    humidity: Optional[float] = None
    radiation: Optional[float] = None
    eto: Optional[float] = None
    compass_rose: Optional[str] = None
    real_eto: Optional[float] = None
    radiation_uv: Optional[float] = None
    processed: int
    created_at: datetime

    class Config:
        from_attributes = True


class WeatherDataSummary(BaseModel):
    """
    Modelo resumido para listados
    """

    id: int
    station_time: datetime
    source: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True
