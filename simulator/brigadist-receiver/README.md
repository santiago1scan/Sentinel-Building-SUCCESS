# Receptor del brigadista

Esta carpeta representa el equipo que llevaría el brigadista. No lo manejo como otro monolito porque el Heltec tiene recursos limitados y solamente necesita escuchar la radio, validar la alerta, avisar y responder el ACK.

- `firmware`: base C++ para cargar por USB en un Heltec WiFi LoRa 32 V3.2 con SX1262.
- `emulator`: receptor Python que uso para comprobar el flujo completo sin tener todavía la placa física.

La trama incluye identificador, nodo, sensor, tipo de evento, valor, umbral y tiempo. El receptor revisa el HMAC, descarta duplicados y devuelve un ACK de radio. Todavía falta conectar los controladores físicos de SX1262, OLED, buzzer, vibrador y botón cuando se confirme la revisión exacta de la placa y la frecuencia permitida.
