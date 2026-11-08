# Monolito Consulta

API para consultas y análisis de datos del sistema Sentinel Builder.

## Descripción

Este es un microservicio FastAPI diseñado para manejar consultas y análisis de datos. Es parte de la arquitectura de microservicios del proyecto Sentinel Builder.

## Requisitos

- Python 3.12+
- PostgreSQL 13+
- pip

## Instalación

### 1. Crear un entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus valores
```

### 4. Ejecutar migraciones (cuando haya)

```bash
alembic upgrade head
```

### 5. Ejecutar la aplicación

```bash
uvicorn app.main:app --reload
```

La API estará disponible en `http://localhost:8000`

## Documentación

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Estructura del Proyecto

```
monolito-consulta/
├── app/
│   ├── api/
│   │   ├── routes/          # Definición de endpoints
│   │   └── deps.py          # Dependencias
│   ├── core/
│   │   ├── config.py        # Configuración
│   │   ├── database.py      # Conexión BD
│   │   ├── exceptions.py    # Excepciones
│   │   └── base_repository.py
│   ├── models/              # Modelos SQLAlchemy
│   ├── repositories/        # Capa de acceso a datos
│   ├── schemas/             # Esquemas Pydantic
│   ├── services/            # Lógica de negocio
│   └── main.py              # Aplicación principal
├── alembic/                 # Migraciones de BD
├── requirements.txt         # Dependencias Python
├── Dockerfile               # Dockerfile
├── .env.example             # Variables de entorno ejemplo
└── README.md
```

## Desarrollo

### Crear una nueva ruta

1. Crear un archivo en `app/api/routes/`
2. Importarlo en `app/api/routes/__init__.py`
3. Incluirlo en `app/main.py`

### Crear un modelo

1. Crear la clase en `app/models/`
2. Crear el repositorio en `app/repositories/`
3. Crear el servicio en `app/services/`
4. Crear el esquema en `app/schemas/`

## Endpoints Disponibles

### Health Check

- `GET /health` - Verificar estado de la API

### Documentación

- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc

## Variables de Entorno

- `DATABASE_URL`: URL de conexión a PostgreSQL
- `APP_ENV`: Ambiente (development, production)

## Docker

### Construir imagen

```bash
docker build -t monolito-consulta .
```

### Ejecutar contenedor

```bash
docker run -p 8000:8000 --env-file .env monolito-consulta
```

## Testing

Hay dos tipos de pruebas:

- **Unitarias y de API** (`tests/unit`, `tests/api`): validan la autenticación de nodos por token y el endpoint MQTT `/auth/node`. No necesitan PostgreSQL, MQTT ni los demás servicios: los repositorios se reemplazan por fakes.
- **De integración** (`tests/integration`): levantan el flujo real simulador → bridge → escucha y verifican con la API de consulta que las lecturas llegan. Escriben datos reales en la base y por eso están desactivadas por defecto. Ver [Pruebas de integración](#pruebas-de-integración).

### Estructura

```
tests/
├── conftest.py                       # Define DATABASE_URL de prueba antes de importar la app
├── helpers.py                        # FakeNodeRepository, FakeTelemetryService, builders de nodos y payloads
├── unit/
│   ├── test_security.py              # Hash SHA-256 del token
│   ├── test_node_auth_service.py     # Autenticación por token y propiedad de bridges
│   ├── test_node_auth_mqtt.py        # Credenciales MQTT (usuario = nodo) y revocación
│   └── test_mqtt_topics.py           # Formato del topic por nodo y coincidencia de bridges
├── api/
│   ├── test_telemetry_auth.py        # Respuestas HTTP del endpoint de telemetría
│   └── test_auth_node_route.py       # Respuestas HTTP del endpoint POST /auth/node
└── integration/
    └── test_rest_pipeline.py         # Simulador → bridge → escucha, verificado con consulta
```

### Qué se prueba

| Caso | Resultado esperado |
|---|---|
| Sin header `X-Node-Token` | `401` y el servicio de telemetría no se ejecuta |
| Header `X-Node-Token` vacío | `401` |
| Token que no pertenece a ningún nodo | `401` |
| Token enviado en la query string | `401` (solo se acepta en el header) |
| Token válido con bridge propio | `202` |
| Token válido con bridge de otro nodo | `403` |
| Token válido en un mensaje con bridge propio y ajeno | `403` |
| Búsqueda por hash | Se consulta el hash del token, nunca el token en claro |
| Usuario MQTT distinto al código del nodo dueño del token | `401` |
| Nodo revocado (`revoked_at` definido) | `401` por REST y por MQTT |
| `POST /auth/node` con usuario y token del mismo nodo | `200` |
| `POST /auth/node` sin contraseña o contraseña vacía | `422` |
| Topic `sentinel/v1/{edificio}/{nodo}/telemetry/aggregate` | Se acepta; otros formatos se descartan |
| Payload con bridges de otro nodo distinto al del topic | Se descarta en el consumidor MQTT |

### Ejecutar en Docker

Desde la raíz del proyecto (usa el `compose.yaml` de la raíz, que ya define la BD `success`):

```bash
docker compose run --rm --no-deps --build monolito-escucha sh -c "pip install -q -r requirements-dev.txt && python -m pytest -q"
```

- `--no-deps` evita levantar PostgreSQL o el broker, que los tests no usan.
- El código se monta como volumen, así que los cambios en `tests/` se ven sin reconstruir la imagen.

### Ejecutar en local

Con el entorno virtual activo, desde `backend/monolito-escucha`:

```bash
pip install -r requirements-dev.txt
pytest -v
```

Los tests no requieren un `.env`: `tests/conftest.py` define un `DATABASE_URL` de prueba si la variable no existe. Si ya tienes una `DATABASE_URL` en el entorno, esa se usa, pero los tests no abren conexiones.

### Pruebas de integración

Verifican el recorrido completo de telemetría por REST:

1. El **simulador** genera un ciclo de lecturas para los dos nodos y lo envía al **bridge**.
2. El **bridge** divide el lote por nodo y entrega cada mensaje a **escucha** con el `X-Node-Token` de su nodo.
3. La prueba consulta a **consulta** (`GET /readings/receiving-node/{id}`) y comprueba que llegaron lecturas nuevas de ambos nodos.

Además comprueba que escucha rechaza con `401` un mensaje sin token y que no guarda nada.

**Estas pruebas escriben lecturas reales en la base de datos `success`.** Cada ejecución agrega filas. Por eso no corren con `pytest` normal: hay que activarlas explícitamente.

#### Precondiciones

- Stack levantado: `monolito-escucha`, `monolito-consulta` y `bridge`.
- Migración aplicada (`alembic upgrade head`), con la columna `node.token_hash`.
- Tokens provisionados para `NODE-FLOOR-1` y `NODE-FLOOR-2`, y `SENTINEL_NODE_TOKENS` definido en el `.env` de la raíz. El bridge necesita esos tokens para entregar por REST.
- El `bridge` debe estar reconstruido con la versión que divide por nodo.

#### Ejecutar en Docker (recomendado)

Desde la raíz del proyecto:

```bash
docker compose --profile test run --rm integration-tests
```

- El servicio `integration-tests` está en el perfil `test`, así que un `docker compose up` normal **no** lo ejecuta.
- Monta el código de `backend/monolito-escucha` y el de `simulator`, y se conecta a la red del stack por nombre de servicio.
- Las variables `RUN_INTEGRATION`, las URLs internas y la ruta del simulador ya están definidas en `compose.yaml`.

#### Ejecutar desde el host

Con el stack levantado y el entorno virtual activo, desde `backend/monolito-escucha`:

```bash
RUN_INTEGRATION=1 pytest tests/integration -v
```

Las URLs por defecto apuntan a `localhost` (`8089` escucha, `8090` consulta, `8766` bridge). Se pueden cambiar con `INTEGRATION_ESCUCHA_URL`, `INTEGRATION_CONSULTA_URL`, `INTEGRATION_BRIDGE_URL` e `INTEGRATION_SIMULATOR_DIR`.

Para que la prueba también levante los servicios con `docker compose up -d --build`, define `SENTINEL_INTEGRATION_COMPOSE=1`. Esto solo funciona desde el repositorio, no dentro del contenedor de pruebas.

#### Qué significa el resultado

```
tests/integration/test_rest_pipeline.py::test_simulator_cycle_is_received_by_backend PASSED
tests/integration/test_rest_pipeline.py::test_rest_without_node_token_is_rejected_and_nothing_is_received PASSED
============================== 2 passed in 30.29s ==============================
```

- Si no defines `RUN_INTEGRATION=1`, las dos pruebas aparecen como `skipped`.
- Si el bridge no responde, la prueba falla antes de tocar la base de datos, con un mensaje como `http://…/health no responde tras 60s`.
- Si el simulador no completa un ciclo, la salida del simulador aparece en el mensaje de error.
- Si el bridge entrega a menos de los dos nodos, el error indica `rest=N` con el valor real.

### Dependencias de test

- `requirements-dev.txt` incluye `requirements.txt` y agrega `pytest==7.4.3` y `pytest-asyncio==0.21.1`.
- La configuración de pytest está en `pyproject.toml` (`pythonpath = ["."]`, `testpaths = ["tests"]`).

## License

Este proyecto es parte de Sentinel Builder.
