# 📚 Documentación - Sentinel Builder Backend

**Guía de navegación por toda la documentación disponible**

---

## 🗂️ Estructura de Documentación

```
backend/
├── DOCUMENTACION.md              ← TÚ ESTÁS AQUÍ
├── ARQUITECTURA.md               ← Arquitectura general
├── ENDPOINTS_RESUMEN.md          ← Referencia rápida de endpoints
├── COMPARATIVA_MONOLITOS.md      ← Guía para elegir servicio
│
├── monolito-escucha/
│   ├── ENDPOINTS.md              ← Endpoints detallados (PRINCIPAL)
│   ├── README.md                 ← Setup y configuración
│   ├── API_BUILDING_ZONE_NODE.md ← Ejemplos de API Building/Zone/Node
│   ├── requirements.txt           ← Dependencias Python
│   ├── docker-compose.yaml       ← Docker Compose config
│   └── ...
│
└── monolito-consulta/
    ├── ENDPOINTS.md              ← Endpoints (legado)
    ├── README.md                 ← Setup legado
    ├── API_BUILDING_ZONE_NODE.md ← Ejemplos legados
    ├── README_ERRORS.md          ← Errores y soluciones
    ├── Idea_entity.md            ← Modelo de datos
    └── ...
```

---

## 📖 Documentos Principales

### 1. **ARQUITECTURA.md** (11 KB)
**¿Qué es?** Visión general de la arquitectura completa  
**Leer si:** Necesitas entender cómo funciona todo el sistema  
**Contiene:**
- Diagrama de arquitectura
- Responsabilidades de cada servicio
- Flujos de datos
- BD compartida
- MQTT Broker
- Despliegue
- Buenas prácticas

**⏱️ Tiempo de lectura:** 10 minutos

---

### 2. **ENDPOINTS_RESUMEN.md** (6.1 KB)
**¿Qué es?** Referencia rápida de todos los endpoints  
**Leer si:** Necesitas recordar una ruta rápidamente  
**Contiene:**
- Lista completa de endpoints
- Query parameters comunes
- Códigos de respuesta
- Ejemplos de cURL
- Flujos comunes

**⏱️ Tiempo de lectura:** 5 minutos

---

### 3. **COMPARATIVA_MONOLITOS.md** (8.1 KB)
**¿Qué es?** Comparación entre Escucha y Consulta  
**Leer si:** No sabes cuál servicio usar  
**Contiene:**
- Tabla comparativa
- Características de cada uno
- Casos de uso
- Matriz de decisión
- Recomendaciones

**⏱️ Tiempo de lectura:** 8 minutos

---

## 🎯 Documentación por Monolito

### Monolito Escucha (Principal)

#### **ENDPOINTS.md** (13 KB) ⭐
**Descripción:** Documentación completa de todos los endpoints  
**Secciones:**
- General
- Health & Status
- MQTT & Telemetría
- Edificios (Buildings)
- Zonas (Zones)
- Nodos (Nodes)
- Tipos de Sensores
- Sensores
- Lecturas (Readings)
- Alertas
- Registros de Conectividad
- Usuarios
- Roles

**Cómo usarlo:**
```
1. Busca el recurso que necesitas (Ctrl+F)
2. Ve a la sección correspondiente
3. Copia el endpoint
4. Consulta parámetros y respuesta
```

#### **README.md** (2.8 KB)
**Descripción:** Setup y configuración del servicio  
**Contiene:**
- Descripción del proyecto
- Requisitos
- Instalación paso a paso
- Variables de entorno
- Ejecución
- Docker support

**Cómo usarlo:**
```
1. Primer uso: sigue los pasos
2. Setup nuevo ambiente: referencia rápida
3. Docker: instrucciones específicas
```

#### **API_BUILDING_ZONE_NODE.md** (6.5 KB)
**Descripción:** Ejemplos de API para Building/Zone/Node  
**Contiene:**
- Ejemplos detallados
- Requests/Responses
- cURL examples
- Casos de uso

**Cómo usarlo:**
```
1. Copia ejemplos de cURL
2. Modifica valores según necesidad
3. Ejecuta en terminal
```

---

### Monolito Consulta (Legado)

#### **ENDPOINTS.md** (3.5 KB)
**Descripción:** Endpoints disponibles (no activos)  
**Nota:** Este monolito es legado, usa **Monolito Escucha**

#### **README.md** 
**Descripción:** Setup (si necesitas usarlo)

#### **API_BUILDING_ZONE_NODE.md**
**Descripción:** Ejemplos legados

#### **README_ERRORS.md** (13 KB)
**Descripción:** Errores comunes y soluciones

#### **Idea_entity.md** (17 KB)
**Descripción:** Modelo de datos y entidades

---

## 🚀 Flujo de Lectura Recomendado

### Para Nuevos Desarrolladores
```
1. Empieza aquí → DOCUMENTACION.md (este archivo)
   ↓
2. Entiende arquitectura → ARQUITECTURA.md
   ↓
3. Aprende a elegir → COMPARATIVA_MONOLITOS.md
   ↓
4. Setup inicial → monolito-escucha/README.md
   ↓
5. Referencia rápida → ENDPOINTS_RESUMEN.md
   ↓
6. Detalle completo → monolito-escucha/ENDPOINTS.md
```

### Para Integración
```
1. Elige servicio → COMPARATIVA_MONOLITOS.md
   ↓
2. Ve endpoints → ENDPOINTS_RESUMEN.md
   ↓
3. Detalle completo → monolito-escucha/ENDPOINTS.md
   ↓
4. Ejemplos → monolito-escucha/API_BUILDING_ZONE_NODE.md
```

### Para Troubleshooting
```
1. Problema en monolito-escucha?
   → monolito-escucha/README.md (sección de troubleshooting si existe)
   
2. Problema en monolito-consulta?
   → monolito-consulta/README_ERRORS.md

3. No sabes endpoint?
   → ENDPOINTS_RESUMEN.md (búsqueda rápida)
   → monolito-escucha/ENDPOINTS.md (detallado)
```

---

## 🔍 Búsquedas Rápidas

### "¿Qué endpoint debo usar?"
→ **ENDPOINTS_RESUMEN.md** + **COMPARATIVA_MONOLITOS.md**

### "¿Cómo creo un edificio?"
→ **monolito-escucha/ENDPOINTS.md** (sección Buildings)  
→ **monolito-escucha/API_BUILDING_ZONE_NODE.md** (ejemplos)

### "¿Cómo obtengo lecturas de un sensor?"
→ **ENDPOINTS_RESUMEN.md** (busca "readings")  
→ **monolito-escucha/ENDPOINTS.md** (sección Readings)

### "¿Cómo activo MQTT?"
→ **ARQUITECTURA.md** (sección MQTT Broker)  
→ **monolito-escucha/README.md** (sección setup)

### "¿Monolito Escucha o Consulta?"
→ **COMPARATIVA_MONOLITOS.md** (respuesta directa)

### "¿Códigos de error?"
→ **ENDPOINTS_RESUMEN.md** (tabla de códigos)  
→ **monolito-consulta/README_ERRORS.md** (detallado)

---

## 📊 Resumen de Contenidos

| Documento | Tamaño | Enfoque | Público |
|-----------|--------|---------|---------|
| ARQUITECTURA.md | 11 KB | Visión general | Todos |
| ENDPOINTS_RESUMEN.md | 6.1 KB | Referencia rápida | Developers |
| COMPARATIVA_MONOLITOS.md | 8.1 KB | Decisiones | Todos |
| monolito-escucha/ENDPOINTS.md | 13 KB | Detalle completo | Developers |
| monolito-escucha/README.md | 2.8 KB | Setup | DevOps |
| monolito-escucha/API_BUILDING_ZONE_NODE.md | 6.5 KB | Ejemplos | Developers |
| monolito-consulta/ENDPOINTS.md | 3.5 KB | Referencia | Histórico |
| monolito-consulta/README_ERRORS.md | 13 KB | Soluciones | Troubleshooting |

---

## ✅ Checklist de Documentación

### Documentación de Arquitectura
- ✅ ARQUITECTURA.md - Visión general
- ✅ COMPARATIVA_MONOLITOS.md - Servicios vs características
- ✅ ENDPOINTS_RESUMEN.md - Lista rápida

### Documentación Monolito Escucha
- ✅ ENDPOINTS.md - Endpoints detallados
- ✅ README.md - Setup y configuración
- ✅ API_BUILDING_ZONE_NODE.md - Ejemplos

### Documentación Monolito Consulta
- ✅ ENDPOINTS.md - Referencia legada
- ✅ README.md - Setup legado
- ✅ README_ERRORS.md - Errores y soluciones
- ✅ Idea_entity.md - Modelo de datos

---

## 🎯 Próximas Mejoras Documentarias

- [ ] Video tutorial de setup
- [ ] Postman collection de endpoints
- [ ] Diagrama de flujo de datos interactivo
- [ ] Casos de uso detallados
- [ ] Guía de contribución
- [ ] FAQ frecuentes
- [ ] API changelog
- [ ] Performance guidelines

---

## 📞 ¿No encuentras lo que buscas?

1. **Busca en ENDPOINTS_RESUMEN.md** (Ctrl+F)
2. **Lee ARQUITECTURA.md** para entender flujos
3. **Consulta COMPARATIVA_MONOLITOS.md** para decisiones
4. **Ve monolito-escucha/ENDPOINTS.md** para detalles
5. **Revisa ejemplos en API_BUILDING_ZONE_NODE.md**

---

## 📋 Información del Documento

- **Versión**: 1.0
- **Fecha**: 2026-10-30
- **Mantenedor**: Sentinel Builder Team
- **Estado**: ✅ Actualizado
- **Total páginas**: ~50 KB de documentación

---

## 🗺️ Mapa de Documentación Visual

```
                        ┌─────────────────┐
                        │  DOCUMENTACION  │
                        │   (Este doc)    │
                        └────────┬────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
          ┌──────────┐     ┌────────────┐   ┌──────────────┐
          │ARQUITECT-│     │  ENDPOINTS │   │ COMPARATIVA  │
          │  URA.md  │     │ RESUMEN.md │   │ MONOLITOS.md │
          └──────────┘     └────────────┘   └──────────────┘
                │                │                │
                │                │                │
          ┌─────▼─────────────────▼────────────────▼─────┐
          │   Monolito Escucha (Principal)                │
          │   ┌─────────────────────────────────────┐    │
          │   ├─ ENDPOINTS.md (detalles)            │    │
          │   ├─ README.md (setup)                  │    │
          │   └─ API_BUILDING_ZONE_NODE.md (ej)    │    │
          └───────────────────────────────────────────────┘
                │
          ┌─────▼─────┐
          │ Monolito  │
          │ Consulta  │
          │ (Legado)  │
          └───────────┘
```

---

**Última actualización**: 2026-10-30  
**Versión**: 1.0  
**Status**: ✅ Completa
