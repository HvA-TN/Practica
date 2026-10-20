
#include <Wire.h>
#include <AS5600.h>
#include <math.h>

// =====================================================
// 1. INSTELLINGEN
// =====================================================

const int pwm_start = 180;
const int pwm_eind  = 255;
const int pwm_stap  = 5;

const unsigned long meetinterval_ms = 100;
const unsigned long meetduur_ms = 10000;

const int N = 100;  // Maximale aantal metingen per periode

// =====================================================
// 2. PINNEN EN VARIABELEN
// =====================================================

const int enablePin = 9;
const int motorPin1 = 10;
const int motorPin2 = 11;

AS5600 sensor;

int pwm_waarde = pwm_start;

float metingen[N];
int aantal_metingen = 0;

unsigned long vorige_meting_ms = 0;
unsigned long start_periode_ms = 0;

bool sweep_klaar = false;

// =====================================================
// 3. FUNCTIES
// =====================================================

// Lees de hoek in graden
float meetHoek() {
  return sensor.readAngle() * 360.0 / 4096.0;
}

// Bereken het gemiddelde
float berekenGemiddelde() {
  float som = 0;
  for (int i = 0; i < aantal_metingen; i++) {
    som += metingen[i];
  }
  return som / aantal_metingen;
}

// Bereken de standaardafwijking
float berekenSTD(float gemiddelde) {
  float som = 0;
  for (int i = 0; i < aantal_metingen; i++) {
    som += pow(metingen[i] - gemiddelde, 2);
  }
  return sqrt(som / (aantal_metingen - 1));
}

// Print de resultaten
void toonResultaten() {

  if (aantal_metingen < 2) return;

  float gemiddelde = berekenGemiddelde();
  float std = berekenSTD(gemiddelde);

  Serial.print(pwm_waarde);
  Serial.print(",");
  Serial.print(gemiddelde, 3);
  Serial.print(",");
  Serial.print(std, 3);
  Serial.print(",");
  Serial.println(aantal_metingen);
}

// =====================================================
// 4. SETUP
// =====================================================

void setup() {

  Wire.begin();
  sensor.begin();

  pinMode(enablePin, OUTPUT);
  pinMode(motorPin1, OUTPUT);
  pinMode(motorPin2, OUTPUT);

  analogWrite(enablePin, 0);

  digitalWrite(motorPin1, LOW);
  digitalWrite(motorPin2, HIGH);

  Serial.begin(115200);
  delay(2000);

  Serial.println("PWM,gemiddelde_deg,STD_deg,N");

  analogWrite(enablePin, pwm_waarde);

  start_periode_ms = millis();
  vorige_meting_ms = start_periode_ms;
}

// =====================================================
// 5. LOOP
// =====================================================

void loop() {

  if (sweep_klaar) return;

  unsigned long tijd = millis();

  // Meet iedere 100 ms de hoek
  if (tijd - vorige_meting_ms >= meetinterval_ms) {

    vorige_meting_ms = tijd;

    if (aantal_metingen < N) {
      metingen[aantal_metingen] = meetHoek();
      aantal_metingen++;
    }
  }

  // Verander de PWM iedere 10 seconden
  if (tijd - start_periode_ms >= meetduur_ms) {

    toonResultaten();

    pwm_waarde += pwm_stap;

    if (pwm_waarde > pwm_eind) {
      analogWrite(enablePin, 0);
      sweep_klaar = true;
      return;
    }

    aantal_metingen = 0;
    start_periode_ms = millis();
    vorige_meting_ms = start_periode_ms;

    analogWrite(enablePin, pwm_waarde);
  }
}
