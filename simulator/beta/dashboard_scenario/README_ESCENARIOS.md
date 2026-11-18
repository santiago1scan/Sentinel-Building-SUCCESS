# Panel de simulación de escenarios de desastre

Este panel independiente permite generar escenarios sintéticos de incendio,
terremoto y caída de energía con el simulador existente. El panel inicia y
administra su propio proceso de `mqtt_sensor_simulator.py`; no puede enviar
comandos a una instancia del simulador iniciada en otra terminal.

El flujo de datos existente se mantiene sin cambios:

```text
mqtt_sensor_simulator.py
    -> POST local /v1/readings
    -> bridge
    -> SQLite
    -> agregación y JSON schema_version 1.0
    -> REST
    -> mock backend
    -> dashboard principal
```

El panel no modifica el contrato JSON ni requiere instalar dependencias nuevas.
Utiliza únicamente la biblioteca estándar de Python. El proyecto sigue
necesitando sus dependencias existentes para ejecutar el backend, el bridge y
el simulador en sus modos correspondientes.

El resumen por archivo de los cambios conservados en el proyecto está en
[`../../RESUMEN_CAMBIOS.md`](../../RESUMEN_CAMBIOS.md).

## Integración y comportamiento actual

El estado final usa el mock backend local con SQLite; no requiere PostgreSQL.
Ambos simuladores envían agregados al mock, aunque cada uno conserva su propia
cola SQLite local. El dashboard principal Beta consulta el estado compartido:
una anomalía reciente de escenario prevalece sobre una lectura normal de Beta
hasta que se publique el `clear`. Las lecturas de más de 90 segundos se marcan
como obsoletas para que una alarma antigua no permanezca activa indefinidamente.

La cadencia normal es de 30 segundos. Activar una anomalía y limpiar el
escenario despierta el productor para publicar el cambio sin esperar ese ciclo.
Las lecturas de ambos simuladores son sintéticas y no son copias entre sí.

## Cambios incluidos desde la integración inicial

- Se corrigieron los enlaces y los puertos para que **Open main dashboard**
  lleve a Beta en `8782`; su API de control usa `8792` y el panel de escenarios
  conserva `8790`.
- Se mantuvo SQLite y se retiró la ruta temporal de PostgreSQL. Beta y
  escenarios guardan sus colas locales y envían sus agregados al mock en
  `8000`.
- Se añadió la consulta compartida de sensores para que el dashboard Beta
  refleje anomalías de escenarios, indique la fuente de las lecturas y marque
  como obsoletas las que tengan más de 90 segundos.
- Se reforzaron los acuses y reintentos de las colas para que un mensaje solo
  se elimine tras confirmación del backend.
- Se ajustó la telemetría periódica a 30 segundos y se hizo inmediata la
  publicación tanto de las anomalías como de su limpieza.

El detalle por archivo, incluida la persistencia de datos y las pruebas, está
en [`../../RESUMEN_CAMBIOS.md`](../../RESUMEN_CAMBIOS.md).

## Archivos

- `scenario_server.py`: servidor HTTP, controlador del proceso del simulador y
  lector de métricas de SQLite en modo de solo lectura.
- `scenario_index.html`: interfaz local con CSS y JavaScript incluidos.
- `README_ESCENARIOS.md`: estas instrucciones.

## Escenarios

| Escenario | Sensores | Efectos sintéticos del simulador | Nodos |
|---|---|---|---|
| Incendio (`fire`) | GRID-EYE (AMG8833) y BME688 | GRID-EYE genera píxeles centrales de 45–60 °C. BME688 genera temperatura de 30–42 °C, humedad de 70–90 %, IAQ de 250–500 y TVOC de 900–3000 ppb. Prioridad `high`. | Piso 1, Piso 2 o ambos; ambos aparecen seleccionados por defecto. |
| Terremoto (`earthquake`) | ADXL355 | Genera vibración anómala con RMS de 0,25–0,8 g y frecuencia de 1–8 Hz. Prioridad `critical`. | Ambos pisos aparecen seleccionados por defecto; se puede elegir un piso. |
| Caída de energía (`power_failure`) | INA219 | Genera voltaje de 10,2–11,0 V, alimentación por batería y `battery_low` cuando el voltaje es inferior a 11 V. Prioridad `critical`. | Se debe elegir exactamente un nodo. |

Un escenario puede ejecutarse manualmente hasta pulsar **Stop all / Return to
normal**, o por una cantidad de segundos configurada en la tarjeta. Solo puede
haber un escenario activo a la vez: al activar otro, el panel envía primero los
comandos `clear` del escenario anterior.

Hay aproximadamente 300 ms entre los comandos de anomalía. Cada comando
`anomaly` despierta el ciclo del simulador. Por ello, el primer agregado de
emergencia puede contener solo el primer sensor activado; el ciclo siguiente
puede contener todos los sensores del escenario.

## Requisitos y puertos

- Python disponible mediante el lanzador `py` (o `python`) en PowerShell.
- Dependencias del backend local: `fastapi` y `uvicorn`; `paho-mqtt` es
  opcional y solo se usa para la salida MQTT.
- Panel: `http://127.0.0.1:8790`
- Mock backend: `http://127.0.0.1:8000`
- Bridge: `http://127.0.0.1:8766`
- Panel Beta de sensores: `http://127.0.0.1:8782`
- API de control de Beta: `http://127.0.0.1:8792`

Los comandos siguientes suponen que la terminal de VS Code inicia en la raíz
`Sentinel-Building-SUCCESS`. Abre cuatro terminales separadas; cada bloque se
ejecuta en su propia terminal. Las rutas de datos relativas del bridge y el
panel se resuelven desde `simulator\beta`.

## Orden de arranque

Inicia los servicios en este orden. No ejecutes una segunda instancia si el
puerto ya está ocupado por el servicio esperado.

Si las dependencias no están instaladas, instálalas una sola vez desde una
terminal nueva:

```powershell
Set-Location .\simulator
py -m pip install -r requirements.txt
```

### 1. Mock backend (SQLite)

En la primera terminal, desde la raíz:

```powershell
Set-Location .\simulator
py -m uvicorn mock_backend.fastapi_app:app --host 127.0.0.1 --port 8000
```

El backend guarda los agregados recibidos en
`simulator\data_api\api_received.db`. No requiere Docker ni PostgreSQL.
Comprueba que está activo con `Invoke-RestMethod http://127.0.0.1:8000/health`;
si devuelve `status: ok`, reutiliza ese proceso en vez de iniciar otro.

### 2. Bridge para el panel de escenarios

En una segunda terminal, desde la raíz:

```powershell
Set-Location .\simulator\beta
py ..\bridge\bridge_service.py `
  --listen-host 127.0.0.1 `
  --listen-port 8766 `
  --interval 30 `
  --api-url http://127.0.0.1:8000 `
  --api-path /api/v1/telemetry/aggregate `
  --data-dir data_bridge
```

El bridge reenvía los agregados en orden y valida el acuse del mock backend;
los que estén pendientes en `data_bridge\bridge_local.db` se reintentan al
llegar nuevas lecturas.

### 3. Panel de escenarios

En una tercera terminal, desde la raíz:

```powershell
Set-Location .\simulator\beta
py .\dashboard_scenario\scenario_server.py `
  --host 127.0.0.1 `
  --port 8790 `
  --bridge-url "http://127.0.0.1:8766" `
  --bridge-port 8766 `
  --interval 30 `
  --simulator-data-dir data_sensor_simulator `
  --data-dir data_bridge
```

Abre `http://127.0.0.1:8790` y pulsa **Start simulator**. No arranques
`mqtt_sensor_simulator.py` manualmente: solo la instancia iniciada por este
panel puede controlarse desde sus botones.
El intervalo de 30 segundos es entre ciclos periódicos de telemetría; al
activar o limpiar una anomalía, el simulador puede generar un ciclo inmediato.

### 4. Panel Beta de sensores

En una cuarta terminal, desde la raíz:

```powershell
Set-Location .\simulator\beta
py .\start_beta.py `
  --no-browser `
  --dashboard-host 127.0.0.1 `
  --dashboard-port 8782 `
  --control-host 127.0.0.1 `
  --control-port 8792 `
  --backend-url "http://127.0.0.1:8000/api/v1"
```

Abre `http://127.0.0.1:8782`. Se usa el puerto de control `8792` para evitar
el conflicto con el panel de escenarios, que escucha en `8790`. `start_beta.py`
también usa `8792` por defecto.

Para detener todo, pulsa primero **Stop all / Return to normal** y luego
**Stop simulator** en el panel de escenarios. Finalmente, presiona `Ctrl+C` en
las terminales de Beta, el bridge y el mock backend.

Las lecturas de ambos paneles se envían al mismo mock backend SQLite. Si no
está disponible, los agregados quedan pendientes en sus respectivas colas
SQLite para reintento. El dashboard principal Beta consulta ese estado
compartido: muestra la fuente de cada sensor y prioriza valores anómalos
recientes de escenarios hasta que se envíen lecturas normales.

Los argumentos disponibles del panel incluyen `--host`, `--port`,
`--bridge-url`, `--bridge-port`, `--interval`, `--simulator-data-dir` y
`--data-dir`. Para ver su ayuda:

```powershell
py .\dashboard_scenario\scenario_server.py --help
```

## Cómo activar y detener escenarios

1. Pulsa **Start simulator**.
2. En la tarjeta del escenario, elige el nodo o nodos afectados.
3. Elige **Manual stop** o **Automatic** e indica una duración entera positiva
   en segundos para el modo automático.
4. Pulsa el botón de activación de la tarjeta.
5. Observa el estado, la prioridad y los registros en el panel de escenarios.
   En el dashboard Beta, las tarjetas afectadas deben indicar **Scenario** y
   mostrar alarma para temperatura y calidad del aire durante Fire.
6. Pulsa **Stop all / Return to normal**. El comando `clear` publica lecturas
   normales inmediatamente; el dashboard Beta debe dejar de mostrar la alarma
   sin esperar los 30 segundos del ciclo periódico.
7. Si también quieres finalizar el proceso, pulsa **Stop simulator**.

En la API del panel, las rutas son:

- `GET /`: interfaz del panel.
- `GET /api/status`: estado, escenario activo, registros, métricas del bridge y
  advertencias.
- `POST /api/scenario/start`: activa `fire`, `earthquake` o `power_failure`.
- `POST /api/scenario/stop`: detiene el escenario y limpia todas las
  combinaciones de nodos y sensores.
- `POST /api/simulator/start`: inicia el simulador.
- `POST /api/simulator/stop`: limpia anomalías, envía `quit` y detiene el
  simulador; si no responde, intenta terminar el proceso.

Ejemplo de activación por PowerShell, con el panel ya en ejecución:

```powershell
$body = @{
  scenario = "power_failure"
  nodes = @("NODE-FLOOR-1")
  duration_s = 45
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8790/api/scenario/start" `
  -ContentType "application/json" `
  -Body $body
```

Para un escenario manual, establece `duration_s` en `$null`. La caída de energía
requiere exactamente un nodo. En incendio y terremoto, la API usa ambos nodos
por defecto si se recibe una lista vacía.

## Verificación de aceptación

Realiza las pruebas con el backend, el bridge, el dashboard y el panel
ejecutándose en ese orden. Inicia el simulador desde el panel antes de activar
cualquier escenario.

1. **Panel e inicio del simulador:** abre `http://127.0.0.1:8790` y pulsa
   **Start simulator**. Comprueba que el indicador muestre **Simulator running**
   y que aparezcan líneas de salida del proceso.
2. **Incendio:** activa **Fire** en ambos pisos. Comprueba en el panel que el
   escenario está activo y que el bridge registra lecturas. Si se configuró un
   backend, comprueba que recibió un agregado con prioridad `high`. El primer
   ciclo puede incluir solo uno de los sensores porque el simulador se despierta
   al recibir cada `anomaly`.
3. **Terremoto:** activa **Earthquake** con ambos pisos seleccionados.
   Comprueba que el escenario esté activo y que el agregado tenga prioridad
   `critical`.
4. **Caída de energía:** selecciona un solo piso y activa **Power failure**.
   Comprueba que el agregado corresponda al único nodo seleccionado. En los
   datos del INA219 debe aparecer `battery_low: true` cuando el voltaje
   generado sea inferior a 11 V; el valor se selecciona aleatoriamente dentro
   del rango del simulador.
5. **Dashboard compartido:** abre `http://127.0.0.1:8782` y confirma que
   `/api/state` muestra `shared_backend.connected: true`. En las tarjetas se
   identifica si la lectura vigente proviene de **Beta** o **Scenario**.
6. **Volver a valores normales:** pulsa **Stop all / Return to normal**. El
   simulador publica el estado normal inmediatamente; si una fuente deja de
   enviar datos, una lectura de más de 90 segundos se marca como obsoleta.
7. **Persistencia y contratos:** los agregados del mock se guardan en
   `simulator\data_api\api_received.db`. El mock acepta JSON 1.0 (escenarios)
   y JSON 2.0 (Beta), y confirma cada mensaje con su `message_uid`.
8. **Colas locales:** si el mock no está disponible, revisa las colas del
   bridge o de Beta; los agregados pendientes se reintentan al recuperar la
   conexión.

Ejemplo de comprobación del backend y el estado compartido:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/sensors/latest |
  ConvertTo-Json -Depth 6
Invoke-RestMethod http://127.0.0.1:8782/api/state |
  Select-Object -ExpandProperty shared_backend
```

## Solución de problemas

### El puerto del panel está ocupado

El puerto predeterminado es 8790. Si ya está en uso, inicia el panel en otro
puerto libre, por ejemplo:

```powershell
py .\dashboard_scenario\scenario_server.py --port 8791
```

Después abre `http://127.0.0.1:8791`. Si el puerto no está disponible, el
servidor muestra el error al iniciarse.

Si el puerto `8000` ya está ocupado, comprueba primero si el mock responde en
`/health`. El error `WinError 10048` indica que ya hay un proceso escuchando
en esa dirección; no inicies una segunda copia. Para reiniciarlo, usa `Ctrl+C`
en la terminal que ejecuta ese proceso y vuelve a arrancarlo una sola vez.

### El bridge está activo o hay un simulador iniciado manualmente

El panel comprueba si el puerto configurado con `--bridge-port` está activo.
Si detecta un bridge activo pero no ha iniciado su propio simulador, muestra
una advertencia. Si ejecutaste el simulador en otra terminal, detenlo allí
antes de iniciar uno desde el panel. El panel no puede controlar el proceso
manual porque no posee su `stdin`.

No inicies una segunda instancia del simulador para el mismo bridge mientras
otra siga activa.

### La base del bridge no aparece

El panel consulta `bridge_local.db` en el directorio indicado por `--data-dir`,
por defecto `data_bridge`. Asegúrate de que el argumento del panel coincide con
`--data-dir` del bridge y de haber iniciado el bridge. La base puede no existir
hasta que el bridge la cree; el panel lo tolera y seguirá mostrando métricas
vacías hasta que pueda leerla.

La lectura de métricas abre SQLite con `mode=ro`; el panel no crea ni modifica
la base del bridge.

### El simulador no se inicia desde el panel

Comprueba que:

- Ejecutas el comando desde una instalación de Python capaz de ejecutar el
  simulador.
- El archivo `mqtt_sensor_simulator.py` está en la raíz del proyecto.
- El bridge ya está escuchando en la URL de `--bridge-url`.
- No hay otra instancia manual del simulador que debas detener.
- La salida del simulador en la sección **Simulator output** no muestra errores.

### No veo la alarma en el dashboard

Confirma que el mock responde en `8000/health`, que el bridge responde en
`8766/health` y que el simulador figura como activo en `8790/api/status`.
También confirma que el dashboard Beta informa
`shared_backend.connected: true` en `8782/api/state`. El simulador de
escenarios y Beta generan datos separados; el dashboard muestra el estado
combinado que recibe el mock.

### La alarma no se limpia

Pulsa **Stop all / Return to normal**. El comando `clear` ahora despierta el
simulador y envía el estado normal sin esperar el ciclo de 30 segundos. Si la
tarjeta indica que la lectura está obsoleta, comprueba que el simulador y el
bridge estén activos y que no haya agregados pendientes.

## Limitaciones conocidas

- Los valores anómalos son rangos aleatorios fijos del simulador, no una
  evolución gradual. El fuego no «crece» y el sismo no «decae». Una evolución
  más realista exigiría modificar el simulador y queda como fase 2 opcional.
- Los datos son sintéticos y no representan mediciones físicas certificadas.
- La separación entre comandos de escenario es de aproximadamente 300 ms.
  Como cada comando `anomaly` despierta un ciclo del simulador, el primer
  agregado de emergencia puede salir con solo el primer sensor activo y el
  siguiente ciclo puede incluir los demás.
- Las lecturas de más de 90 segundos se consideran obsoletas. Esto evita que
  una alarma histórica siga activa si el simulador se detiene sin enviar el
  `clear`.
- El panel solo controla la instancia del simulador que él mismo lanza; no
  puede adjuntarse a una instancia iniciada en otra terminal.