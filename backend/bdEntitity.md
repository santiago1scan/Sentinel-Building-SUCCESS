Table building {
  building_id integer [pk, increment]
  name varchar
  address varchar
}

Table zone {
  zone_id integer [pk, increment]
  building_id integer [ref: > building.building_id]
  name varchar
  floor integer
}

Table node {
  node_id integer [pk, increment]
  code varchar
  name varchar
  zone_id integer [ref: > zone.zone_id]
  ip_address varchar
  local_storage_mb integer
  last_signal_received_at timestamp
  registered_at timestamp
}

Table sensor_type {
  sensor_type_id integer [pk, increment]
  name varchar
  sampling_interval integer
  default_unit varchar
  normal_minimum numeric
  normal_maximum numeric
}

Table sensor {
  sensor_id integer [pk, increment]
  code varchar
  primary_node_id integer [ref: > node.node_id]
  connection_type varchar
  sensor_type_id integer [ref: > sensor_type.sensor_type_id]
  connection_address varchar
}

Table connectivity_log {
  connectivity_id integer [pk, increment]
  node_id integer [ref: > node.node_id]
  started_at timestamp
  ended_at timestamp
}

Table reading {
  reading_id integer [pk, increment]
  sensor_id integer [ref: > sensor.sensor_id]
  receiving_node_id integer [ref: > node.node_id]
  sequence_number integer
  measured_at timestamp
  received_at timestamp
  measured_value numeric
}

Table app_role {
  role_code varchar [pk]
  name varchar
}

Table app_user {
  user_id integer [pk, increment]
  email varchar
  full_name varchar
  password_hash varchar
  is_active boolean
  last_login_at timestamp
  created_at timestamp
  role_code varchar [ref: > app_role.role_code]
}

Table alert {
  alert_id integer [pk, increment]
  event_uuid uuid
  reading_id integer [ref: > reading.reading_id]
  handled_by_user_id integer [ref: > app_user.user_id]
  alert_code varchar
  generated_at timestamp
}


2. Diagrama ERD en Mermaid

erDiagram
    building ||--o{ zone : "contains"
    zone ||--o{ node : "houses"
    node ||--o{ connectivity_log : "logs"
    node ||--o{ sensor : "primary node for"
    sensor_type ||--o{ sensor : "defines type for"
    sensor ||--o{ reading : "produces"
    node ||--o{ reading : "receives"
    reading ||--o{ alert : "triggers"
    app_user ||--o{ alert : "handles"
    app_role ||--o{ app_user : "assigned to"

    building {
        int building_id PK
        string name
        string address
    }

    zone {
        int zone_id PK
        int building_id FK
        string name
        int floor
    }

    node {
        int node_id PK
        string code
        string name
        int zone_id FK
        string ip_address
        int local_storage_mb
        timestamp last_signal_received_at
        timestamp registered_at
    }

    sensor_type {
        int sensor_type_id PK
        string name
        int sampling_interval
        string default_unit
        numeric normal_minimum
        numeric normal_maximum
    }

    sensor {
        int sensor_id PK
        string code
        int primary_node_id FK
        string connection_type
        int sensor_type_id FK
        string connection_address
    }

    connectivity_log {
        int connectivity_id PK
        int node_id FK
        timestamp started_at
        timestamp ended_at
    }

    reading {
        int reading_id PK
        int sensor_id FK
        int receiving_node_id FK
        int sequence_number
        timestamp measured_at
        timestamp received_at
        numeric measured_value
    }

    app_role {
        string role_code PK
        string name
    }

    app_user {
        int user_id PK
        string email
        string full_name
        string password_hash
        boolean is_active
        timestamp last_login_at
        timestamp created_at
        string role_code FK
    }

    alert {
        int alert_id PK
        uuid event_uuid
        int reading_id FK
        int handled_by_user_id FK
        string alert_code
        timestamp generated_at
    }
