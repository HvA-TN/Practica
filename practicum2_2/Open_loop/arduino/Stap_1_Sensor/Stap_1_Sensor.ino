#include <Wire.h>
#include <AS5600.h>

// Stap 1: sluit alleen de AS5600-hoeksensor aan.
const unsigned long meetinterval_ms = 100;
AS5600 sensor;

void setup() {
  Wire.begin();
  sensor.begin();
  Serial.begin(115200);
}

void loop() {
  // De sensor geeft 4096 stappen per volledige omwenteling.
  float hoek_graden = sensor.readAngle() * 360.0 / 4096.0;

  // Bekijk de hoek in de Serial Monitor of Serial Plotter.
  Serial.print("Hoek:");
  Serial.println(hoek_graden, 2);

  delay(meetinterval_ms);
}
