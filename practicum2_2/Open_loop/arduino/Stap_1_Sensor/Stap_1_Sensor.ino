#include <Wire.h>
#include <AS5600.h>

// Instellingen

const unsigned long meetinterval_ms = 100;

// AS5600-hoeksensor (I2C)
const int sensorSDA = A4;
const int sensorSCL = A5;
const uint8_t sensorAdres = 0x36;

// Sensorobject
AS5600 sensor(&Wire);


void setup() {
  Serial.begin(115200);

  // I2C initialiseren
  // UNO R4 Minima: SDA = A4, SCL = A5
  Wire.begin();

  // Sensor initialiseren
  sensor.begin();
}

void loop() {
  // Hoek uitlezen (12-bit: 0 t/m 4095)
  float hoek_graden = sensor.readAngle() * 360.0 / 4096.0;

  // Hoek naar Serial Monitor of Serial Plotter sturen
  Serial.print("Hoek:");
  Serial.println(hoek_graden, 3);

  delay(meetinterval_ms);
}