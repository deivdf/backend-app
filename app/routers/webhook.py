from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta
from app.models import (
    DataReceived,
    DataResponse,
    WeatherStationData,
    WeatherDataOut,
    WeatherDataSummary,
)
from app.database import get_db
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhook", response_model=DataResponse)
async def receive_weather_data(data: DataReceived, db: Session = Depends(get_db)):
    """
    Endpoint para recibir datos meteorológicos del servidor externo
    Los datos se guardan en PostgreSQL
    """
    try:
        db_data = WeatherStationData(
            station_time=data.stationTime,
            source=data.source,
            temperature=data.temperature,
            precipitation=data.precipitation,
            real_precipitation=data.realPrecipitation,
            presure=data.presure,
            wind_speed=data.windSpeed,
            wind_direction=data.windDirection,
            humidity=data.humidity,
            radiation=data.radiation,
            eto=data.eto,
            compass_rose=data.compassRose,
            real_eto=data.realETO,
            radiation_uv=data.radiationUV,
            active_sensor=data.activeSensor,
            solar_panel=data.solarPanel,
            open_door=data.openDoor,
            low_battery=data.lowBattery,
            observations=data.observations,
        )

        db.add(db_data)
        db.commit()
        db.refresh(db_data)

        logger.info(
            f"Datos meteorológicos guardados - ID: {db_data.id}, Fuente: {data.source}, Temp: {data.temperature}°C"
        )

        return DataResponse(
            success=True,
            message="Datos meteorológicos recibidos y guardados correctamente",
            id=db_data.id,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error procesando datos meteorológicos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al guardar datos: {str(e)}")


@router.get("/data", response_model=List[WeatherDataSummary])
async def get_all_weather_data(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(
        100, ge=1, le=1000, description="Número máximo de registros a retornar"
    ),
    source: Optional[str] = Query(None, description="Filtrar por fuente/sensor"),
    start_date: Optional[datetime] = Query(
        None, description="Fecha inicial (ISO 8601)"
    ),
    end_date: Optional[datetime] = Query(None, description="Fecha final (ISO 8601)"),
    db: Session = Depends(get_db),
):
    """
    Endpoint para que Flutter consulte los datos meteorológicos almacenados
    Soporta paginación y filtros múltiples
    """
    query = db.query(WeatherStationData)

    if source:
        query = query.filter(WeatherStationData.source == source)

    if start_date:
        query = query.filter(WeatherStationData.station_time >= start_date)

    if end_date:
        query = query.filter(WeatherStationData.station_time <= end_date)

    data = (
        query.order_by(desc(WeatherStationData.station_time))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return data


@router.get("/data/{data_id}", response_model=WeatherDataOut)
async def get_weather_data_by_id(data_id: int, db: Session = Depends(get_db)):
    """
    Obtener datos meteorológicos específicos por ID
    """
    data = db.query(WeatherStationData).filter(WeatherStationData.id == data_id).first()

    if not data:
        raise HTTPException(
            status_code=404, detail=f"No se encontraron datos con ID {data_id}"
        )

    return data


@router.get("/data/source/{source_name}", response_model=List[WeatherDataOut])
async def get_data_by_source(
    source_name: str,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Obtener los últimos datos de una fuente/sensor específico
    """
    data = (
        db.query(WeatherStationData)
        .filter(WeatherStationData.source == source_name)
        .order_by(desc(WeatherStationData.station_time))
        .limit(limit)
        .all()
    )

    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron datos para la fuente '{source_name}'",
        )

    return data


@router.get("/data/latest/all")
async def get_latest_from_all_sources(db: Session = Depends(get_db)):
    """
    Obtener la lectura más reciente de cada estación/sensor
    Útil para dashboards en tiempo real
    """

    subquery = (
        db.query(
            WeatherStationData.source, func.max(WeatherStationData.id).label("max_id")
        )
        .group_by(WeatherStationData.source)
        .subquery()
    )

    latest_data = (
        db.query(WeatherStationData)
        .join(subquery, WeatherStationData.id == subquery.c.max_id)
        .all()
    )

    return latest_data


@router.get("/statistics/source/{source_name}")
async def get_statistics_by_source(
    source_name: str,
    hours: int = Query(
        24, ge=1, le=720, description="Horas hacia atrás para calcular estadísticas"
    ),
    db: Session = Depends(get_db),
):
    """
    Obtener estadísticas de una fuente específica (promedios, máximos, mínimos)
    """
    time_threshold = datetime.utcnow() - timedelta(hours=hours)

    stats = (
        db.query(
            func.avg(WeatherStationData.temperature).label("avg_temp"),
            func.max(WeatherStationData.temperature).label("max_temp"),
            func.min(WeatherStationData.temperature).label("min_temp"),
            func.avg(WeatherStationData.humidity).label("avg_humidity"),
            func.avg(WeatherStationData.wind_speed).label("avg_wind_speed"),
            func.max(WeatherStationData.wind_speed).label("max_wind_speed"),
            func.count(WeatherStationData.id).label("total_records"),
        )
        .filter(
            WeatherStationData.source == source_name,
            WeatherStationData.station_time >= time_threshold,
        )
        .first()
    )

    if not stats or stats.total_records == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No hay datos suficientes para '{source_name}' en las últimas {hours} horas",
        )

    return {
        "source": source_name,
        "period_hours": hours,
        "statistics": {
            "temperature": {
                "average": round(stats.avg_temp, 2) if stats.avg_temp else None,
                "maximum": round(stats.max_temp, 2) if stats.max_temp else None,
                "minimum": round(stats.min_temp, 2) if stats.min_temp else None,
            },
            "humidity": {
                "average": round(stats.avg_humidity, 2) if stats.avg_humidity else None
            },
            "wind_speed": {
                "average": round(stats.avg_wind_speed, 2)
                if stats.avg_wind_speed
                else None,
                "maximum": round(stats.max_wind_speed, 2)
                if stats.max_wind_speed
                else None,
            },
            "total_records": stats.total_records,
        },
    }


@router.get("/predict/rain_probability/{source_name}")
async def get_rain_probability(
    source_name: str,
    hours: int = Query(
        6, ge=1, le=48, description="Horas hacia atrás para evaluar la probabilidad"
    ),
    db: Session = Depends(get_db),
):
    """
    Estima la probabilidad de lluvia para una fuente específica
    basado en datos recientes.
    **Nota:** Este es un modelo simplificado y no un pronóstico profesional.
    """
    time_threshold = datetime.utcnow() - timedelta(hours=hours)

    recent_data = (
        db.query(WeatherStationData)
        .filter(
            WeatherStationData.source == source_name,
            WeatherStationData.station_time >= time_threshold,
        )
        .order_by(WeatherStationData.station_time.asc())
        .all()
    )

    if len(recent_data) < 2:
        raise HTTPException(
            status_code=404,
            detail=f"No hay suficientes datos para '{source_name}' en las últimas {hours} horas para hacer una predicción.",
        )

    probability = 0
    pressure_change = 0.0

    humidities = [d.humidity for d in recent_data if d.humidity is not None]
    avg_humidity = sum(humidities) / len(humidities) if humidities else 0

    if avg_humidity > 90:
        probability += 30
    elif avg_humidity > 75:
        probability += 15

    first_pressure = recent_data[0].presure
    last_pressure = recent_data[-1].presure
    if first_pressure is not None and last_pressure is not None:
        pressure_change = last_pressure - first_pressure
        if pressure_change < -1.5:
            probability += 35
        elif pressure_change < -0.5:
            probability += 15

    total_precipitation = sum(
        d.real_precipitation for d in recent_data if d.real_precipitation is not None
    )
    if total_precipitation > 0.1:
        probability += 25

    final_probability = min(probability, 100)

    return {
        "source": source_name,
        "period_hours": hours,
        "rain_probability": final_probability,
        "records_analyzed": len(recent_data),
        "debug_info": {
            "average_humidity": round(avg_humidity, 2),
            "pressure_change": round(pressure_change, 2),
            "total_precipitation": round(total_precipitation, 2),
        },
    }


@router.put("/data/{data_id}/mark-processed")
async def mark_as_processed(data_id: int, db: Session = Depends(get_db)):
    """
    Marcar un registro como procesado
    """
    data = db.query(WeatherStationData).filter(WeatherStationData.id == data_id).first()

    if not data:
        raise HTTPException(status_code=404, detail="Dato no encontrado")

    data.processed = 1
    db.commit()

    return {"success": True, "message": "Dato marcado como procesado", "id": data_id}


@router.delete("/data/{data_id}")
async def delete_weather_data(data_id: int, db: Session = Depends(get_db)):
    """
    Eliminar un registro específico (usar con precaución)
    """
    data = db.query(WeatherStationData).filter(WeatherStationData.id == data_id).first()

    if not data:
        raise HTTPException(status_code=404, detail="Dato no encontrado")

    db.delete(data)
    db.commit()

    return {"success": True, "message": "Dato eliminado correctamente", "id": data_id}


@router.get("/sources/list")
async def list_all_sources(db: Session = Depends(get_db)):
    """
    Listar todas las fuentes/sensores disponibles
    """
    sources = (
        db.query(WeatherStationData.source)
        .distinct()
        .order_by(WeatherStationData.source)
        .all()
    )

    return {"total": len(sources), "sources": [s[0] for s in sources]}
