from datetime import datetime
from enum import Enum
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field


# --- Enums para campos de tipo fijo/categoría ---

class PriorityEnum(str, Enum):
    NORMAL = "normal"
    HIGH = "high"
    LOW = "low"

class QualityEnum(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    DEGRADED = "degraded"

class MeasurementTypeEnum(str, Enum):
    TEMPERATURE = "temperature"
    AIR_QUALITY = "air_quality"
    MOTION = "motion"
    ELECTRICAL = "electrical"


# --- Modelos de payload específicos por tipo de sensor ---

class TemperatureSensorData(BaseModel):
    average_avg_c: Optional[float] = None
    maximum_avg_c: Optional[float] = None
    maximum_c: Optional[float] = None
    hot_pixels_max: Optional[int] = None
    matrix_size: Optional[str] = None

class AirQualitySensorData(BaseModel):
    temperature_avg_c: Optional[float] = None
    humidity_avg_percent: Optional[float] = None
    pressure_avg_hpa: Optional[float] = None
    iaq_avg: Optional[float] = None
    tvoc_avg_ppb: Optional[float] = None

class MotionSensorData(BaseModel):
    x_avg_g: Optional[float] = None
    y_avg_g: Optional[float] = None
    z_avg_g: Optional[float] = None
    rms_avg_g: Optional[float] = None
    rms_max_g: Optional[float] = None
    frequency_avg_hz: Optional[float] = None

class ElectricalSensorData(BaseModel):
    voltage_avg_v: Optional[float] = None
    voltage_min_v: Optional[float] = None
    voltage_max_v: Optional[float] = None
    current_avg_ma: Optional[float] = None
    power_avg_mw: Optional[float] = None
    battery_low: Optional[bool] = None

# Unión flexible para aceptar los tipos estructurados o un diccionario genérico en caso de nuevos sensores
SensorDataPayload = Union[
    TemperatureSensorData,
    AirQualitySensorData,
    MotionSensorData,
    ElectricalSensorData,
    Dict[str, Any]
]


# --- DTOs del dominio principal ---

class SensorDTO(BaseModel):
    sensor_uid: str
    sensor_code: str
    sensor_model: str
    measurement_type: Union[MeasurementTypeEnum, str]
    sample_count: int
    data: SensorDataPayload

class BridgeDTO(BaseModel):
    node_uid: str
    node_code: str
    node_name: str
    floor: int
    zone_uid: str
    zone_code: str
    sensors: List[SensorDTO] = Field(default_factory=list)

class WindowDTO(BaseModel):
    start: datetime
    end: datetime
    duration_seconds: float
    sample_count: int

class TelemetryAggregateDTO(BaseModel):
    schema_version: str = Field(description="Versión del esquema del mensaje")
    message_uid: str
    message_type: str

    building_uid: str
    building_code: str

    generated_at: datetime
    sent_at: datetime
    sequence_number: int

    priority: Union[PriorityEnum, str]
    quality: Union[QualityEnum, str]
    delivery_policy: str

    delivery_status: str
    transport: str

    window: WindowDTO
    bridges: List[BridgeDTO] = Field(default_factory=list)