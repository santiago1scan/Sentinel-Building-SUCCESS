"""seed the sensor catalog: the 4 sensor types of the node and the variables each one measures

Without these rows nobody can register sensors: sensor_type and sensor_metric were empty in every new database.

- One sensor_type per physical sensor (the name is the model, as in Parametros_Normales_Cauca_Colombia.xlsx).
- One sensor_metric per variable, with the code the backend expects (temperature_c; a summary sends
  temperature_c__avg|max|min, stored as aggregations of that same metric in reading.aggregation). As of 17-Nov the
  repo bridge still sends temperature_avg_c, iaq_avg, voltage_avg_v...: until it changes, those land in new metrics
  without a range (pending with the bridge owner).
- Normal ranges: 6 from the Excel (sheet Umbrales_Normales) and 9 from the team (thermal camera, TVOC, vibration and
  power; 16-Nov-2026). All 18 have a range since 17-Nov:
  - Pressure 815-835 hPa: the Excel's sea-level range (1013.7-1024) taken to Popayan's ~1,740 m (x0.811 =
    822-831 hPa) with a margin. An estimate until it is measured on site.
  - power_source and battery_low are 0/1 flags: normal is 0, physical 0-1. They raise their own technical notice
    (ON_BATTERY_POWER, BATTERY_LOW) and are never judged against the range, so the range only documents them.
- Values match app/analytics/ranges.py DEFAULT_RANGES, so a metric created here or on first sight is the same.

Idempotent: rows that already exist (same type name, or same type + metric code) are left as they are.
downgrade removes the catalog rows (these type names and metric codes) nobody uses yet: no sensors, readings or
alerts point to them. It cannot tell a seeded row from an identical one created before.

Revision ID: c3f8a2d6b9e1
Revises: d5a9e3b1c7f2
Create Date: 2026-11-17 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3f8a2d6b9e1"
down_revision: Union[str, Sequence[str], None] = "d5a9e3b1c7f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SAMPLING_INTERVAL_S = 30  # the simulator and the bridge read every 30 s

# (name, default_unit): accelerometer, 8x8 thermal camera, environment/air quality, power monitor
SENSOR_TYPES = [
    ("ADXL355", "g"),
    ("AMG8833", "°C"),
    ("BME688", None),
    ("INA219", None),
]

# (sensor type, metric_code, name, unit, normal_min, normal_max, physical_min, physical_max, alarm_below)
METRICS = [
    ("ADXL355", "x_g", "Aceleración eje X", "g", -0.01, 0.01, None, None, True),
    ("ADXL355", "y_g", "Aceleración eje Y", "g", -0.01, 0.01, None, None, True),
    ("ADXL355", "z_g", "Aceleración eje Z", "g", 0.99, 1.01, None, None, True),
    ("ADXL355", "rms_g", "Vibración RMS", "g", 0.0002, 0.0071, None, None, True),
    ("ADXL355", "frequency_hz", "Frecuencia de vibración", "Hz", 3, 4, None, None, True),
    ("AMG8833", "maximum_c", "Temperatura máxima de la imagen", "°C", 17, 35, None, None, True),
    ("AMG8833", "average_c", "Temperatura promedio de la imagen", "°C", 17, 26, None, None, True),
    ("AMG8833", "hot_pixels", "Píxeles calientes", "píxeles", 0, 0, None, None, True),
    ("BME688", "temperature_c", "Temperatura", "°C", 10, 31, -40, 85, True),
    ("BME688", "humidity_percent", "Humedad relativa", "%", 72.78, 94.48, 0, 100, True),
    ("BME688", "pressure_hpa", "Presión", "hPa", 815, 835, 300, 1100, True),
    # IAQ below 51 is "Excellent" air (Bosch table): out of range, but not an alarm.
    ("BME688", "iaq_index", "Calidad del aire (IAQ)", "IAQ", 51, 100, 0, 500, False),
    # TVOC: team range 0.3-0.5 ppm, stored in ppb as the sensor sends it; below 0.3 ppm is cleaner air, not an alarm.
    ("BME688", "tvoc_ppb", "Compuestos orgánicos volátiles (TVOC)", "ppb", 300, 500, None, None, False),
    ("INA219", "bus_voltage_v", "Voltaje", "V", 11, 12, None, None, True),
    ("INA219", "current_ma", "Corriente", "mA", 300, 500, None, None, True),
    ("INA219", "power_mw", "Potencia", "mW", 3300, 6000, None, None, True),
    # Flags stored as 0/1: 1 = the node runs on battery / the battery is low. Normal = 0.
    ("INA219", "power_source", "Funciona con batería", None, 0, 0, 0, 1, True),
    ("INA219", "battery_low", "Batería baja", None, 0, 0, 0, 1, True),
]

TYPE_NAMES = tuple(name for name, _ in SENSOR_TYPES)


def upgrade() -> None:
    conn = op.get_bind()
    for name, unit in SENSOR_TYPES:
        conn.execute(sa.text(
            "INSERT INTO sensor_type (name, sampling_interval, default_unit) VALUES (:name, :interval, :unit) "
            "ON CONFLICT (name) DO NOTHING"
        ), {"name": name, "interval": SAMPLING_INTERVAL_S, "unit": unit})

    for type_name, code, name, unit, low, high, pmin, pmax, alarm_below in METRICS:
        conn.execute(sa.text(
            "INSERT INTO sensor_metric (sensor_type_id, metric_code, name, unit, normal_minimum, normal_maximum, "
            "physical_minimum, physical_maximum, alarm_below, alarm_above) "
            "SELECT sensor_type_id, :code, :name, :unit, :low, :high, :pmin, :pmax, :alarm_below, true "
            "FROM sensor_type WHERE name = :type_name "
            "ON CONFLICT (sensor_type_id, metric_code) DO NOTHING"
        ), {"type_name": type_name, "code": code, "name": name, "unit": unit, "low": low, "high": high,
            "pmin": pmin, "pmax": pmax, "alarm_below": alarm_below})


def downgrade() -> None:
    conn = op.get_bind()
    params = {"types": list(TYPE_NAMES), "codes": [m[1] for m in METRICS]}
    conn.execute(sa.text(
        "DELETE FROM sensor_metric m USING sensor_type t "
        "WHERE m.sensor_type_id = t.sensor_type_id AND t.name = ANY(:types) AND m.metric_code = ANY(:codes) "
        "AND NOT EXISTS (SELECT 1 FROM reading r WHERE r.metric_id = m.metric_id) "
        "AND NOT EXISTS (SELECT 1 FROM alert a WHERE a.metric_id = m.metric_id)"
    ), params)
    conn.execute(sa.text(
        "DELETE FROM sensor_type t WHERE t.name = ANY(:types) "
        "AND NOT EXISTS (SELECT 1 FROM sensor s WHERE s.sensor_type_id = t.sensor_type_id) "
        "AND NOT EXISTS (SELECT 1 FROM sensor_metric m WHERE m.sensor_type_id = t.sensor_type_id)"
    ), {"types": params["types"]})
