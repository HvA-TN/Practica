#include <Wire.h>
#include <AS5600.h>

// Stap 2: voeg de motor en de L298N-motordriver toe.
// Verander de PWM-waarde en upload opnieuw (0 = uit, 255 = maximaal).
const int pwm_waarde = 60;
const unsigned long meetinterval_ms = 100;

const int enablePin = 9;  // Naar ENA van de motordriver (PWM).
const int motorPin1 = 10; // Naar IN1.
const int motorPin2 = 11; // Naar IN2.

AS5600 sensor;

void setup() {
  Wire.begin();
  sensor.begin();
  Serial.begin(115200);

  pinMode(enablePin, OUTPUT);
  pinMode(motorPin1, OUTPUT);
  pinMode(motorPin2, OUTPUT);

  analogWrite(enablePin, 0);
  digitalWrite(motorPin1, LOW);
  digitalWrite(motorPin2, HIGH);

  // Na het uploaden of resetten gaat de motor op deze PWM draaien.
  analogWrite(enablePin, pwm_waarde);
}

void loop() {
  float hoek_graden = sensor.readAngle() * 360.0 / 4096.0;

  Serial.print("Hoek:");
  Serial.println(hoek_graden, 2);

  delay(meetinterval_ms);
}
