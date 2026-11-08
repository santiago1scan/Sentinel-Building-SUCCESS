# Sentinel Builder - Backend

Monolito de escucha para ingesta de lecturas y gestión de alertas, conectado a PostgreSQL via Docker.

## Requisitos

- Docker Desktop / Docker Engine
- Docker Compose v2+

## Estructura

```
backend/
├── compose.yaml                 # Orquestación completa (postgres + monolito)
├── sumothings_db/               # PostgreSQL config y schema SQL
│   ├── compose.yaml
│   ├── success_db.sql           # Schema completo (10 tablas)
│   └── .env.example
└── monolito-escucha/            # FastAPI application
    ├── app/
    │   ├── api/routes/          # health, readings, alerts
    │   ├── core/                # config, database
    │   ├── models/              # SQLAlchemy models
    │   ├── repositories/        # Repository pattern
    │   ├── schemas/             # Pydantic DTOs
    │   └── services/            # Business logic
    ├── alembic/                 # Migraciones (baseline + futuras)
    ├── Dockerfile
    └── pyproject.toml
```

## Levantar el entorno completo

### 1. Clonar y posicionarse
```bash
cd /home/santiago/Documentos/sentinel-builder/backend
```

### 2. Configurar variables de entorno
```bash
cp sumothings_db/.env.example .env
# Editar .env si se desea cambiar credenciales
```

Contenido `.env`:
```env
POSTGRES_DB=success
POSTGRES_USER=admin
POSTGRES_PASSWORD=change_me
APP_ENV=development
```

### 3. Levantar servicios
```bash
docker compose up -d --build
```

Esto crea:
- **postgres** (puerto 5432, interno) - Base de datos PostgreSQL 16
- **monolito-escucha** (puerto 8089) - API FastAPI

### 4. Verificar estado
```bash
# Ver contenedores
docker compose ps

# Ver logs del monolito
docker logs monolito_escucha -f

# Healthcheck
curl http://localhost:8089/health
# {"status":"healthy","database":"connected"}
```

### 5. Acceder a la API
- **Swagger UI**: http://localhost:8089/docs
- **ReDoc**: http://localhost:8089/redoc
- **OpenAPI JSON**: http://localhost:8089/openapi.json

## Endpoints principales

### Lecturas (Create + Read)
```bash
# Crear lectura
curl -X POST http://localhost:8089/readings \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_id": 1,
    "receiving_node_id": 1,
    "measured_at": "2024-01-15T10:30:00Z",
    "measured_value": 25.5,
    "sequence_number": 1
  }'

# Listar todas
curl http://localhost:8089/readings

# Por ID
curl http://localhost:8089/readings/1

# Por sensor
curl http://localhost:8089/readings/sensor/1

# Última por sensor
curl http://localhost:8089/readings/sensor/1/latest

# Por rango de fechas
curl "http://localhost:8089/readings/time-range/?start=2024-01-15T00:00:00Z&end=2024-01-16T00:00:00Z"
```

### Alertas (CRUD completo)
```bash
# Crear alerta
curl -X POST http://localhost:8089/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "event_uuid": "evt-001",
    "reading_id": 1,
    "alert_code": "HIGH_TEMP"
  }'

# Listar todas
curl http://localhost:8089/alerts

# No atendidas
curl http://localhost:8089/alerts/unhandled

# Por usuario
curl http://localhost:8089/alerts/user/1

# Por lectura
curl http://localhost:8089/alerts/reading/1

# Obtener con lectura relacionada
curl http://localhost:8089/alerts/1/with-reading

# Actualizar (acknowledge)
curl -X PATCH http://localhost:8089/alerts/1 \
  -H "Content-Type: application/json" \
  -d '{"handled_by_user_id": 1}'

# Eliminar
curl -X DELETE http://localhost:8089/alerts/1
```

## Datos de prueba (requeridos para FK)

Antes de crear lecturas/alertas, poblar tablas base:
```bash
docker exec -i success_db psql -U admin -d success << 'EOF'
INSERT INTO building (building_id, name, address) VALUES (1, 'Test Building', '123 Test St');
INSERT INTO zone (zone_id, building_id, name, floor) VALUES (1, 1, 'Zone 1', 1);
INSERT INTO node (node_id, code, name, zone_id, ip_address, registered_at) VALUES (1, 'NODE-001', 'Test Node', 1, '192.168.1.100', NOW());
INSERT INTO sensor_type (sensor_type_id, name, sampling_interval, default_unit, normal_minimum, normal_maximum) VALUES (1, 'Temperature', 60, 'Celsius', -40, 85);
INSERT INTO sensor (sensor_id, code, primary_node_id, sensor_type_id, connection_type, connection_address) VALUES (1, 'SENSOR-001', 1, 1, 'MQTT', 'topic/sensor/1');
INSERT INTO app_role (role_code, name) VALUES ('admin', 'Administrator');
INSERT INTO app_user (user_id, email, full_name, password_hash, is_active, role_code) VALUES (1, 'admin@test.com', 'Admin User', 'hash', true, 'admin');
EOF
```

## Migraciones (Alembic)

El proyecto usa **baseline migration** - la BD ya existe con schema completo.

```bash
# Ver migración actual
docker exec monolito_escucha alembic current

# Crear nueva migración (tras cambios en modelos)
docker exec monolito_escucha alembic revision --autogenerate -m "descripcion_cambio"

# Aplicar migraciones
docker exec monolito_escucha alembic upgrade head

# Rollback (si aplica)
docker exec monolito_escucha alembic downgrade -1
```

## Parar y limpiar

```bash
# Parar (mantiene volúmenes)
docker compose down

# Parar y eliminar volúmenes (reset BD)
docker compose down -v
```

## Desarrollo local (sin Docker para la app)

```bash
# 1. Solo BD en Docker
docker compose up -d postgres

# 2. Crear venv e instalar deps
cd monolito-escucha
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# 3. Variables de entorno
cp .env.example .env
# DATABASE_URL ya apunta a localhost:5432

# 4. Correr app con reload
uvicorn app.main:app --host 0.0.0.0 --port 8089 --reload
```

## Puertos

| Servicio | Puerto Interno | Puerto Host |
|----------|----------------|-------------|
| PostgreSQL | 5432 | 5432 (solo localhost) |
| Monolito-Escucha | 8089 | 8089 |

## Troubleshooting

### Error: "relation does not exist"
```bash
# Re-ejecutar schema SQL
docker exec -i success_db psql -U admin -d success < sumothings_db/success_db.sql
```

### Error: "ForeignKeyViolationError"
Verificar que existan los registros referenciados (sensor, node, user, etc.)

### Error: "database files are incompatible"
```bash
# Reset completo (elimina datos)
docker compose down -v && docker compose up -d --build
```

### Puerto 8089 ocupado
Cambiar en `compose.yaml`:
```yaml
ports:
  - "8090:8089"  # host:container
```

## Arquitectura de datos

Tablas principales (ver `sumothings_db/success_db.sql`):
- `building` → `zone` → `node` → `sensor` → `reading`
- `sensor_type` → `sensor`
- `app_role` → `app_user` → `alert`
- `reading` → `alert`
- `node` → `connectivity_log`

Índices optimizados para consultas por sensor/fecha y alertas por usuario.