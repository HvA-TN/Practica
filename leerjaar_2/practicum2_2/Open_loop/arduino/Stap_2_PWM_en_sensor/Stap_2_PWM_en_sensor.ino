#include <Wire.h>
#include <AS5600.h>

// Instellingen

const int pwm_waarde = 60;
const unsigned long meetinterval_ms = 100;

// AS5600-hoeksensor (I2C)
const int sensorSDA = A4;
const int sensorSCL = A5;
const uint8_t sensorAdres = 0x36;

// L298N-motordriver
const int enablePin = 9;   // ENA (PWM)
const int motorPin1 = 10;  // IN1
const int motorPin2 = 11;  // IN2

// Sensorobject
AS5600 sensor(&Wire);

void setup() {
  Serial.begin(115200);

  // I2C initialiseren
  // UNO R4 Minima: SDA = A4, SCL = A5
  Wire.begin();

  // Sensor initialiseren
  sensor.begin();

  // Motorpinnen instellen
  pinMode(enablePin, OUTPUT);
  pinMode(motorPin1, OUTPUT);
  pinMode(motorPin2, OUTPUT);

  // Motor aanvankelijk uitschakelen
  analogWrite(enablePin, 0);

  // Draairichting instellen
  digitalWrite(motorPin1, LOW);
  digitalWrite(motorPin2, HIGH);

  // Motor starten met ingestelde PWM
  analogWrite(enablePin, pwm_waarde);
}

void loop() {
  // Hoek uitlezen (12-bit: 0 t/m 4095)
  float hoek_graden = sensor.readAngle() * 360.0 / 4096.0;

  // Hoek naar Serial Plotter sturen
  Serial.print("Hoek:");
  Serial.println(hoek_graden, 2);

  delay(meetinterval_ms);
}