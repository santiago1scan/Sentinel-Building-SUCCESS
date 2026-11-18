#include <Arduino.h>
#include "protocol.hpp"

// En esta placa solo dejo lo que realmente irá al brigadista:
// radio SX1262, validación de la trama, ACK y avisos por pantalla/sonido.

void setup() {
  Serial.begin(115200);
  // Aquí terminaré la configuración cuando confirmemos la revisión de la
  // placa, la banda permitida, la antena y los pines físicos.
}

void loop() {
  // Por ahora este comportamiento se prueba con el emulador de la Beta.
  delay(100);
}
