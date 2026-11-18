# Resumen de cambios del simulador

Este documento describe los cambios conservados en `simulator` para ejecutar
el panel de escenarios y la simulación Beta usando el mock backend local
SQLite, además de las modificaciones relacionadas con sus dashboards,
persistencia, puertos y documentación.

## Decisión y arquitectura final

La integración final usa SQLite y el mock backend local; no usa PostgreSQL,
Docker ni el backend principal. Durante el trabajo se probó una ruta temporal
hacia PostgreSQL, pero esos cambios se retiraron cuando se confirmó que el
proyecto debía seguir usando SQLite. No quedaron migraciones ni seeds de
PostgreSQL en el estado final.

Los paneles generan lecturas independientes y las envían como agregados al
mismo mock:

```text
Escenarios:
mqtt_sensor_simulator.py -> bridge de escenarios (8766)
                         -> mock SQLite (8000)

Beta:
simulator_v2 de Beta -> mock SQLite (8000)

Dashboard principal Beta (8782) -> GET /api/v1/sensors/latest
```

Compartir el backend no hace que ambos simuladores produzcan las mismas
lecturas. El dashboard principal presenta el estado más reciente por nodo y
tipo de sensor, e indica si la fuente fue **Beta** o **Scenario**.

## Puertos y datos locales

| Servicio | Puerto | Persistencia local |
|---|---:|---|
| Mock backend SQLite | 8000 | `simulator\data_api\api_received.db` |
| Bridge de escenarios | 8766 | `simulator\beta\data_bridge\bridge_local.db` |
| Dashboard principal Beta | 8782 | Resúmenes en `simulator\beta\data` |
| Panel de escenarios | 8790 | Estado e interfaz del panel |
| API de control Beta | 8792 | API de control del simulador Beta |
| Simulador clásico controlado por escenarios | — | Directorio `simulator\beta\data_sensor_simulator` |

Cada panel mantiene su propia cola local. Si el mock no está disponible, los
agregados pendientes permanecen en la SQLite del emisor y se reintentan al
recuperar la conexión. El mock guarda agregados, no el histórico de muestras
crudas de Beta.

## Cambios conservados por archivo

### Panel de escenarios

- `beta\dashboard_scenario\scenario_server.py`: panel local con API para
  iniciar y detener el simulador, activar y limpiar incendios, terremotos y
  cortes de energía, controlar la duración del escenario y mostrar registros
  y métricas del bridge. Resuelve rutas de datos desde el directorio Beta,
  inicia su propia instancia de `mqtt_sensor_simulator.py` y usa un intervalo
  predeterminado de 30 segundos.
- `beta\dashboard_scenario\scenario_index.html`: interfaz para seleccionar el
  escenario y los nodos, observar el estado y acceder al dashboard principal
  Beta en `8782`.
- `beta\dashboard_scenario\README_ESCENARIOS.md`: comandos de VS Code /
  PowerShell, orden de inicio, puertos, rutas SQLite, uso y verificación de
  ambos paneles, además de solución de problemas.

### Mock backend y estado compartido

- `mock_backend\fastapi_app.py`: acepta agregados de escenarios JSON 1.0 y de
  Beta JSON 2.0; guarda los mensajes en SQLite, deduplica por `message_uid`,
  devuelve acuses con lecturas y errores, y expone `/api/v1/sensors/latest`.
  También crea y completa el estado más reciente por fuente, nodo y tipo de
  sensor, incluyendo el estado previo de la base existente.
- El endpoint combina las fuentes dando precedencia a la anomalía vigente de
  mayor gravedad por sensor. Una lectura de más de 90 segundos se marca como
  obsoleta; evita conservar indefinidamente una alarma antigua si una fuente
  deja de enviar datos.
- `mock_backend\test_fastapi_app.py`: cubre contratos de ambos simuladores,
  deduplicación, prioridad de una alarma de escenarios, limpieza y caducidad
  frente a datos recientes de Beta.

### Simulador y bridge de escenarios

- `mqtt_sensor_simulator.py`: un comando `anomaly` despierta el productor para
  publicar inmediatamente; ahora `clear` también lo despierta para publicar
  lecturas normales sin esperar el siguiente ciclo periódico.
- `test_mqtt_sensor_simulator.py`: comprueba que limpiar una anomalía despierta
  al productor.
- `bridge\bridge_service.py`: usa el mock en `8000` y
  `/api/v1/telemetry/aggregate` como destino predeterminado, reenvía pendientes
  en orden y solo confirma la entrega cuando la respuesta coincide con el
  mensaje y sus lecturas. El ciclo predeterminado es de 30 segundos.

### Simulador y dashboard Beta

- `beta\start_beta.py`: configura la URL del mock y la comparte con el
  simulador y el dashboard. Los tokens de nodo son opcionales para el mock
  local. El dashboard principal usa `8782` y el control Beta `8792`, separado
  del panel de escenarios en `8790`.
- `beta\simulator_v2\run_simulation.py`: admite tokens vacíos para el mock
  local y utiliza `8792` como puerto de control predeterminado.
- `beta\dashboard_react_v2\react_dashboard_server.py`: consulta el endpoint
  compartido y lo expone en `/api/state`; si el mock no está disponible, usa
  las lecturas locales de Beta.
- `beta\dashboard_react_v2\index.html`: muestra la fuente de las lecturas y
  aplica los estados visuales según la gravedad y la antigüedad de cada
  sensor. Lecturas obsoletas quedan señaladas y no conservan una alarma roja.
- `beta\compose.yaml` y `beta\Dockerfile`: publican el control de Beta en
  `8792`, evitando el conflicto con el panel de escenarios.
- `beta\tests\test_bridge_rest_replay.py`: cubre el reintento ordenado de
  agregados pendientes y su retención cuando el backend informa errores.

### Configuración y documentación compartida

- `requirements.txt`: dependencias compartidas para el mock FastAPI/Uvicorn y
  el simulador MQTT opcional.
- `beta\.env.example`: ejemplo de configuración de la URL del mock y de
  tokens vacíos para el backend local.
- `beta\BACKEND_INTEGRATION.md`: contrato, campos de confirmación, persistencia
  y comandos de integración con el mock SQLite.
- `beta\README.md`: inicio de Beta, puertos actualizados y consulta del estado
  compartido.
- `README.md`: acceso directo a la guía de escenarios y a este resumen.

## Comportamiento de alarmas

El período normal de telemetría es de 30 segundos. Las anomalías y el comando
de limpieza activan un ciclo inmediato. Al probar Fire, los sensores de
temperatura y calidad del aire pueden entrar en alarma; al pulsar **Stop all /
Return to normal**, se envían lecturas normales y se limpia el estado del
dashboard sin esperar los 30 segundos.

El dashboard clasifica las lecturas según sus métricas: movimiento entra en
alarma desde `0.25 g` RMS; temperatura desde `40 °C`; calidad del aire desde
`IAQ 250`; y voltaje desde menos de `11 V` o `battery_low`. Los umbrales de
advertencia son, respectivamente, `0.05 g`, `30 °C`, `IAQ 120` y menos de
`11.8 V`.

## Verificación realizada

Se verificó el flujo de Fire de extremo a extremo: el mock y el dashboard Beta
mostraron lecturas `Scenario` con prioridad alta; después de limpiar el
escenario, el backend mostró lecturas normales. También se ejecutaron las
pruebas del mock, las pruebas de Beta y la prueba del comando `clear`. Una
prueba opcional contra un backend externo requiere una configuración que no
forma parte de esta integración SQLite.

