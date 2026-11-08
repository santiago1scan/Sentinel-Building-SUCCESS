Necesito que implementes las entidades ORM y repositories del backend de Sentinel Building utilizando FastAPI + SQLAlchemy 2.x + PostgreSQL.

IMPORTANTE:
- El modelo debe seguir EXACTAMENTE el diagrama ER proporcionado.
- No inventar campos, FK ni relaciones.
- No agregar relaciones que no aparezcan en el modelo.
- Mantener exactamente los nombres de tablas y columnas indicados.
- Utilizar SQLAlchemy 2.x con Mapped y mapped_column.
- Utilizar relationship() y back_populates para las relaciones ORM.
- Separar modelos ORM, schemas Pydantic y repositories.
- Los repositories deben encargarse únicamente del acceso a datos.
- No colocar lógica HTTP ni HTTPException dentro de los repositories.
- No colocar lógica de negocio dentro de los repositories.

==================================================
ENTIDADES
==================================================

1. BUILDING

Tabla:

building

Campos:

- building_id: Integer, PK
- name: String
- address: String

Relación:

Building 1:N Zone

Un building contiene múltiples zones.

Relación ORM:

building.zones -> List[Zone]

==================================================
2. ZONE
==================================================

Tabla:

zone

Campos:

- zone_id: Integer, PK
- building_id: Integer, FK -> building.building_id
- name: String
- floor: Integer

Relaciones:

Zone N:1 Building

Zone 1:N Node

Relaciones ORM:

zone.building -> Building
zone.nodes -> List[Node]

Foreign Key:

zone.building_id -> building.building_id

==================================================
3. NODE
==================================================

Tabla:

node

Campos:

- node_id: Integer, PK
- code: String, UNIQUE
- name: String
- zone_id: Integer, FK -> zone.zone_id
- ip_address: String
- local_storage_mb: Integer
- last_signal_received_at: DateTime
- registered_at: DateTime

Relaciones:

Node N:1 Zone

Node 1:N Sensor

Node 1:N Reading como nodo receptor

Node 1:N ConnectivityLog

Relaciones ORM:

node.zone -> Zone
node.sensors -> List[Sensor]
node.readings_received -> List[Reading]
node.connectivity_logs -> List[ConnectivityLog]

Foreign Key:

node.zone_id -> zone.zone_id

IMPORTANTE:

El campo ip_address corresponde a la dirección IP del nodo.

==================================================
4. SENSOR_TYPE
==================================================

Tabla:

sensor_type

Campos:

- sensor_type_id: Integer, PK
- name: String
- sampling_interval: Integer
- default_unit: String
- normal_minimum: Float
- normal_maximum: Float

Relación:

SensorType 1:N Sensor

Un tipo de sensor puede estar asociado con múltiples sensores.

Relación ORM:

sensor_type.sensors -> List[Sensor]

==================================================
5. SENSOR
==================================================

Tabla:

sensor

Campos:

- sensor_id: Integer, PK
- code: String, UNIQUE
- primary_node_id: Integer, FK -> node.node_id
- connection_type: String
- sensor_type_id: Integer, FK -> sensor_type.sensor_type_id
- connection_address: String

Relaciones:

Sensor N:1 Node

Sensor N:1 SensorType

Sensor 1:N Reading

IMPORTANTE:

Sensor NO tiene relación directa con User.

Sensor NO tiene user_id.

Sensor NO tiene FK hacia app_user.

La relación entre Sensor y User NO debe implementarse.

Relaciones ORM:

sensor.primary_node -> Node
sensor.sensor_type -> SensorType
sensor.readings -> List[Reading]

Foreign Keys:

sensor.primary_node_id -> node.node_id

sensor.sensor_type_id -> sensor_type.sensor_type_id

==================================================
6. READING
==================================================

Tabla:

reading

Campos:

- reading_id: Integer, PK
- sensor_id: Integer, FK -> sensor.sensor_id
- receiving_node_id: Integer, FK -> node.node_id
- sequence_number: Integer
- measured_at: DateTime
- received_at: DateTime
- measured_value: Float

Relaciones:

Reading N:1 Sensor

Reading N:1 Node como nodo receptor

Reading 1:N Alert

Relaciones ORM:

reading.sensor -> Sensor
reading.receiving_node -> Node
reading.alerts -> List[Alert]

Foreign Keys:

reading.sensor_id -> sensor.sensor_id

reading.receiving_node_id -> node.node_id

IMPORTANTE:

La relación con el nodo es mediante receiving_node_id.

No utilizar primary_node_id de Sensor para representar el nodo receptor de una lectura.

Un Sensor tiene un primary_node_id que representa su nodo principal.

Una Reading tiene receiving_node_id que representa el nodo que recibió dicha lectura.

==================================================
7. ALERT
==================================================

Tabla:

alert

Campos:

- alert_id: Integer, PK
- event_uuid: UUID, UNIQUE
- reading_id: Integer, FK -> reading.reading_id
- handled_by_user_id: Integer, FK -> app_user.user_id
- alert_code: String
- generated_at: DateTime

Relaciones:

Alert N:1 Reading

Alert N:1 AppUser mediante handled_by_user_id

IMPORTANTE:

Alert SÍ está relacionada con AppUser.

La relación se realiza mediante:

alert.handled_by_user_id -> app_user.user_id

NO crear una relación Alert -> Sensor directamente mediante una FK sensor_id.

El sensor asociado a una alerta se obtiene indirectamente:

Alert -> Reading -> Sensor

Por lo tanto:

alert.reading.sensor

permite obtener el sensor que originó la lectura asociada a la alerta.

Relaciones ORM:

alert.reading -> Reading
alert.handled_by_user -> AppUser

Foreign Keys:

alert.reading_id -> reading.reading_id

alert.handled_by_user_id -> app_user.user_id

==================================================
8. CONNECTIVITY_LOG
==================================================

Tabla:

connectivity_log

Campos:

- connectivity_id: Integer, PK
- node_id: Integer, FK -> node.node_id
- started_at: DateTime
- ended_at: DateTime

Relación:

ConnectivityLog N:1 Node

Un nodo puede tener múltiples registros de conectividad.

Relación ORM:

connectivity_log.node -> Node

Foreign Key:

connectivity_log.node_id -> node.node_id

==================================================
9. APP_USER
==================================================

Tabla:

app_user

Campos:

- user_id: Integer, PK
- email: String, UNIQUE
- full_name: String
- password_hash: String
- is_active: Boolean
- last_login_at: DateTime
- created_at: DateTime
- role_code: Integer, FK -> app_role.role_code

Relaciones:

AppUser N:1 AppRole

AppUser 1:N Alert

Relaciones ORM:

app_user.role -> AppRole
app_user.handled_alerts -> List[Alert]

Foreign Key:

app_user.role_code -> app_role.role_code

IMPORTANTE:

La relación entre User y Alert representa al usuario que atiende o gestiona la alerta.

La FK está en alert:

alert.handled_by_user_id -> app_user.user_id

NO agregar una FK user_id en sensor.

==================================================
10. APP_ROLE
==================================================

Tabla:

app_role

Campos:

- role_code: Integer, PK
- name: String

Relación:

AppRole 1:N AppUser

Relación ORM:

app_role.users -> List[AppUser]

Foreign Key:

app_user.role_code -> app_role.role_code

==================================================
RELACIONES COMPLETAS
==================================================

Building 1:N Zone

Zone 1:N Node

Node 1:N Sensor

SensorType 1:N Sensor

Node 1:N Reading como nodo receptor

Sensor 1:N Reading

Reading 1:N Alert

AppUser 1:N Alert

AppRole 1:N AppUser

Node 1:N ConnectivityLog

==================================================
DIAGRAMA LÓGICO DE RELACIONES
==================================================

Building
    |
    | 1:N
    v
Zone
    |
    | 1:N
    v
Node
    |
    | 1:N
    v
Sensor
    |
    | N:1
    v
SensorType


Sensor
    |
    | 1:N
    v
Reading
    |
    | 1:N
    v
Alert
    |
    | N:1
    v
AppUser
    |
    | N:1
    v
AppRole


Node
    |
    | 1:N
    v
ConnectivityLog


Reading
    |
    | N:1
    v
Node

==================================================
RESUMEN DE FOREIGN KEYS
==================================================

zone.building_id
    -> building.building_id

node.zone_id
    -> zone.zone_id

sensor.primary_node_id
    -> node.node_id

sensor.sensor_type_id
    -> sensor_type.sensor_type_id

reading.sensor_id
    -> sensor.sensor_id

reading.receiving_node_id
    -> node.node_id

alert.reading_id
    -> reading.reading_id

alert.handled_by_user_id
    -> app_user.user_id

connectivity_log.node_id
    -> node.node_id

app_user.role_code
    -> app_role.role_code

==================================================
RESUMEN DE UNIQUE
==================================================

node.code
sensor.code
alert.event_uuid
app_user.email

==================================================
PUNTOS IMPORTANTES DEL MODELO
==================================================

1. Building contiene Zones.

2. Zone contiene Nodes.

3. Node tiene Sensors.

4. Sensor pertenece a un SensorType.

5. Sensor pertenece a un Node mediante primary_node_id.

6. Sensor genera Readings.

7. Reading indica qué Sensor la generó mediante sensor_id.

8. Reading también indica qué Node la recibió mediante receiving_node_id.

9. Alert pertenece a Reading mediante reading_id.

10. Alert pertenece a AppUser mediante handled_by_user_id.

11. NO existe relación directa Sensor -> AppUser.

12. NO existe sensor.user_id.

13. Para obtener el Sensor de una Alert:

    alert.reading.sensor

14. Para obtener el usuario que atiende una Alert:

    alert.handled_by_user

15. Para obtener el Sensor y el usuario que atiende una alerta:

    alert.reading.sensor
    alert.handled_by_user

16. AppUser pertenece a AppRole mediante role_code.

17. Node tiene múltiples ConnectivityLog.

==================================================
SQLALCHEMY RELATIONSHIPS
==================================================

Building:

zones -> List[Zone]

Zone:

building -> Building
nodes -> List[Node]

Node:

zone -> Zone
sensors -> List[Sensor]
readings_received -> List[Reading]
connectivity_logs -> List[ConnectivityLog]

Sensor:

primary_node -> Node
sensor_type -> SensorType
readings -> List[Reading]

SensorType:

sensors -> List[Sensor]

Reading:

sensor -> Sensor
receiving_node -> Node
alerts -> List[Alert]

Alert:

reading -> Reading
handled_by_user -> AppUser

ConnectivityLog:

node -> Node

AppUser:

role -> AppRole
handled_alerts -> List[Alert]

AppRole:

users -> List[AppUser]

==================================================
REPOSITORIES
==================================================

Crear un repository independiente para cada entidad.

Estructura:

repositories/
    building_repository.py
    zone_repository.py
    node_repository.py
    sensor_type_repository.py
    sensor_repository.py
    reading_repository.py
    alert_repository.py
    connectivity_log_repository.py
    app_user_repository.py
    app_role_repository.py

==================================================
BUILDING REPOSITORY
==================================================

BuildingRepository debe implementar:

- create
- get_by_id
- get_all
- update
- delete

Consultas adicionales:

- get_zones(building_id)

==================================================
ZONE REPOSITORY
==================================================

ZoneRepository debe implementar:

- create
- get_by_id
- get_all
- update
- delete

Consultas adicionales:

- get_by_building(building_id)

==================================================
NODE REPOSITORY
==================================================

NodeRepository debe implementar:

- create
- get_by_id
- get_all
- update
- delete
- get_by_code

Consultas adicionales:

- get_by_zone(zone_id)
- get_sensors(node_id)
- get_connectivity_logs(node_id)
- get_received_readings(node_id)

==================================================
SENSOR_TYPE REPOSITORY
==================================================

SensorTypeRepository debe implementar:

- create
- get_by_id
- get_all
- update
- delete

Consultas adicionales:

- get_sensors(sensor_type_id)

==================================================
SENSOR REPOSITORY
==================================================

SensorRepository debe implementar:

- create
- get_by_id
- get_all
- update
- delete
- get_by_code

Consultas adicionales:

- get_by_primary_node(primary_node_id)
- get_by_sensor_type(sensor_type_id)
- get_readings(sensor_id)

IMPORTANTE:

NO crear:

- get_by_user
- user relationship
- user_id

porque Sensor no tiene relación directa con AppUser.

==================================================
READING REPOSITORY
==================================================

ReadingRepository debe implementar:

- create
- get_by_id
- get_all

Consultas adicionales:

- get_by_sensor(sensor_id)
- get_by_receiving_node(receiving_node_id)
- get_by_sequence_number(sequence_number)
- get_alerts(reading_id)

Las lecturas representan mediciones históricas. No implementar update/delete salvo que exista un caso de uso explícito que lo requiera.

==================================================
ALERT REPOSITORY
==================================================

AlertRepository debe implementar:

- create
- get_by_id
- get_all
- update

Consultas adicionales:

- get_by_event_uuid(event_uuid)
- get_by_reading(reading_id)
- get_by_handled_user(user_id)
- get_unhandled()

IMPORTANTE:

La consulta del sensor de una alerta debe hacerse mediante la relación:

Alert -> Reading -> Sensor

No agregar sensor_id directamente en Alert.

==================================================
CONNECTIVITY LOG REPOSITORY
==================================================

ConnectivityLogRepository debe implementar:

- create
- get_by_id
- get_all
- update

Consultas adicionales:

- get_by_node(node_id)
- get_active_by_node(node_id)

==================================================
APP USER REPOSITORY
==================================================

AppUserRepository debe implementar:

- create
- get_by_id
- get_all
- update
- delete
- get_by_email

Consultas adicionales:

- get_by_role(role_code)
- get_handled_alerts(user_id)

IMPORTANTE:

El campo password_hash debe almacenar únicamente el hash de la contraseña.

Nunca almacenar contraseñas en texto plano.

==================================================
APP ROLE REPOSITORY
==================================================

AppRoleRepository debe implementar:

- create
- get_by_code
- get_all
- update
- delete

Consultas adicionales:

- get_users(role_code)

==================================================
ESTRUCTURA DE MODELOS
==================================================

Crear o adaptar los modelos SQLAlchemy siguiendo esta estructura conceptual:

models/
    building.py
    zone.py
    node.py
    sensor_type.py
    sensor.py
    reading.py
    alert.py
    connectivity_log.py
    app_user.py
    app_role.py

Cada modelo debe contener:

- __tablename__
- columnas
- PK
- FK
- Unique constraints cuando corresponda
- relationship()
- back_populates

==================================================
ESTRUCTURA DE SCHEMAS
==================================================

Crear schemas Pydantic separados de los modelos ORM:

schemas/
    building.py
    zone.py
    node.py
    sensor_type.py
    sensor.py
    reading.py
    alert.py
    connectivity_log.py
    app_user.py
    app_role.py

Crear schemas apropiados para:

- Create
- Update
- Response

No exponer password_hash en los schemas de respuesta de AppUser.

==================================================
ORDEN DE IMPLEMENTACIÓN
==================================================

Implementar primero los modelos SQLAlchemy.

Orden:

1. building
2. app_role
3. sensor_type
4. zone
5. node
6. app_user
7. sensor
8. reading
9. connectivity_log
10. alert

Después implementar los repositories.

Después implementar los schemas Pydantic.

==================================================
REGLAS FINALES
==================================================

- Seguir el modelo ER exactamente.
- No inventar relaciones.
- No inventar columnas.
- No cambiar los nombres de las columnas.
- No agregar Sensor -> AppUser.
- No agregar sensor.user_id.
- Alert sí tiene handled_by_user_id.
- Alert sí está relacionada con AppUser.
- Alert está relacionada con Sensor de forma indirecta mediante Reading.
- Reading tiene tanto sensor_id como receiving_node_id.
- Sensor tiene primary_node_id.
- No confundir primary_node_id con receiving_node_id.
- AppUser tiene role_code.
- AppRole utiliza role_code como PK.
- Node.code es UNIQUE.
- Sensor.code es UNIQUE.
- Alert.event_uuid es UNIQUE.
- AppUser.email es UNIQUE.
- ConnectivityLog pertenece a Node.
- Mantener separación entre ORM, schemas y repositories.
- Revisar el código existente antes de crear archivos nuevos.
- Si ya existe una implementación equivalente, modificarla en lugar de duplicarla.
- No hacer cambios destructivos innecesarios.
- Si existe una discrepancia entre el código existente y este modelo, señalarla antes de modificarla.
