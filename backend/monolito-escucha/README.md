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

```bash
pytest
```

## License

Este proyecto es parte de Sentinel Builder.
