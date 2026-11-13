// Stap 5: voeg hoekbegrenzing, sensorbewaking en een vergrendelde foutstop toe.
// Stel grenzen samen met de begeleider vast; dit zijn voorlopige waarden.

#include <Wire.h>
#include <AS5600.h>
#include <PID_v1.h>
#include <stdlib.h>
#include <math.h>

// ==========================================
// 1. HARDWARE
// ==========================================

const int enablePin = 9;
const int motorPin1 = 10;
const int motorPin2 = 11;

AS5600 sensor;

// ==========================================
// 2. VARIABELEN
// ==========================================

int pwm = 0;
int maxPWM = 255;
const double minHoek = -10;
double maxHoek = 80;
bool hoekStop = false;
double werkhoek = 0, pidPWM = 0, doelhoek = 40, beginhoek = 90;
PID regelaar(&werkhoek, &pidPWM, &doelhoek, 2, 0, 0, DIRECT);
bool pidIngesteld = false, pidActief = false, continu = false;
unsigned long meetduur_ms = 30000, start_ms = 0;

unsigned long meetinterval_ms = 100;
unsigned long vorige_meting_ms = 0;

unsigned long laatste_heartbeat_ms = 0;
const unsigned long watchdog_ms = 3000;

bool meten = false;

// Buffer voor seriële commando's
String invoer = "";

void stopPID() {
  regelaar.SetMode(MANUAL);
  pidPWM = 0;
  pidActief = false;
}

// Controleer de gecorrigeerde werkhoek voor iedere PID-aansturing.
bool controleerMaxHoek() {
  bool uitlezenOK = sensor.lastError() == AS5600_OK;
  bool verbonden = sensor.isConnected();
  byte status = sensor.readStatus();
  bool sensorOK = uitlezenOK && verbonden && sensor.lastError() == AS5600_OK &&
                  (status & 0x38) == 0x20;
  if (sensorOK && isfinite(werkhoek) &&
      werkhoek >= minHoek && werkhoek <= maxHoek) return true;
  stopPID();
  meten = false;
  pidIngesteld = false;
  hoekStop = true;
  pwm = 0;
  analogWrite(enablePin, 0);
  Serial.println(sensorOK ? "ERROR:HOEKBEREIK" : "ERROR:SENSOR");
  return false;
}

// Zelfde CONFIG-velden als de Python-aanroep; tijden in milliseconden.
bool configurePID(String tekst) {
  double v[9];
  const char *next = tekst.c_str();
  for (int i = 0; i < 9; i++) {
    char *end;
    v[i] = strtod(next, &end);
    if (end == next || !isfinite(v[i]) || (i < 8 ? *end != ',' : *end != 0)) return false;
    next = end + 1;
  }
  if (v[0] < -180 || v[0] > 180) return false;
  for (int i = 1; i <= 3; i++) if (v[i] < 0 || v[i] > 1000) return false;
  if (v[4] < 0 || v[4] > 255 || v[4] != floor(v[4]) ||
      v[5] < 20 || v[5] > 600000 || v[5] != floor(v[5]) ||
      v[6] < 20 || v[6] > 1000 || v[6] != floor(v[6]) ||
      (v[7] != 0 && v[7] != 1) || (v[7] == 0 && v[5] < v[6])) return false;
  if (v[8] <= minHoek || v[8] > 180 || v[0] < minHoek || v[0] > v[8]) return false;
  maxHoek = v[8];
  hoekStop = false;
  doelhoek = v[0];
  regelaar.SetTunings(v[1], v[2], v[3]);
  maxPWM = (int)v[4];
  // PID_v1 accepteert geen gelijke grenzen. Bij maxPWM=0 slaan we Compute over.
  regelaar.SetOutputLimits(0, maxPWM > 0 ? maxPWM : 1);
  meetduur_ms = v[5];
  meetinterval_ms = v[6];
  regelaar.SetSampleTime((int)v[6]);
  continu = v[7] == 1;
  return true;
}


// ==========================================
// 3. FUNCTIES
// ==========================================

// Motor aansturen met debuguitvoer
void stelPWMIn(int waarde) {

  if (waarde < 0 || waarde > 255) return;

  // Alleen melden als de PWM verandert
  if (waarde != pwm) {

    pwm = waarde;
    analogWrite(enablePin, pwm);

    Serial.print("DEBUG_PWM:");
    Serial.println(pwm);
  }
}

// Hoek meten
float meetHoek() {

  sensor.lastError(); // Wis oude fouten voor deze hoekmeting.
  return sensor.readAngle() * 360.0 / 4096.0;
}

// Commando vanuit Python verwerken
void verwerkCommando(String commando) {

  commando.trim();

  // Heartbeat
  if (commando == "PING") {

    laatste_heartbeat_ms = millis();
    return;
  }

  if (commando == "HELLO") {
    meten = false; stopPID(); stelPWMIn(0); pidIngesteld = false;
    Serial.println("PID_READY"); return;
  }
  if (commando.startsWith("OFFSET:")) {
    meten = false; stopPID(); stelPWMIn(0); pidIngesteld = false;
    String tekst = commando.substring(7);
    char *end;
    double value = strtod(tekst.c_str(), &end);
    if (end == tekst.c_str() || *end != 0 || !isfinite(value) || value < 0 || value >= 360) {
      Serial.println("ERROR:OFFSET"); return;
    }
    beginhoek = value; Serial.println("OFFSET_OK"); return;
  }
  if (commando.startsWith("CONFIG:")) {
    meten = false; stopPID(); stelPWMIn(0);
    pidIngesteld = configurePID(commando.substring(7));
    Serial.println(pidIngesteld ? "CONFIG_OK" : "ERROR:CONFIG"); return;
  }

  // Na een hoekstop is een nieuwe geldige CONFIG nodig.
  if (hoekStop && (commando == "START" || commando.startsWith("PWM:"))) {
    Serial.println("ERROR:VERGRENDELD"); return;
  }

  // PWM instellen
  if (commando.startsWith("PWM:")) {

    String waardeTekst = commando.substring(4);
    waardeTekst.trim();

    if (waardeTekst.length() == 0) return;

    // Controleer of alle tekens cijfers zijn
    for (unsigned int i = 0; i < waardeTekst.length(); i++) {
      if (!isDigit(waardeTekst[i])) return;
    }

    int waarde = waardeTekst.toInt();

    if (waarde >= 0 && waarde <= 255) {

      // Geen handmatige motorsturing buiten de bewaakte PID-regeling.
      if (waarde != 0) { Serial.println("ERROR:GEBRUIK_PID"); return; }
      stelPWMIn(0);
      laatste_heartbeat_ms = millis();
    }
  }

  // PID-regelperiode blijft gelijk aan de CONFIG-instelling.
  else if (commando.startsWith("DT:")) {

    unsigned long waarde = commando.substring(3).toInt();

    if (!pidActief && waarde >= 10 && waarde <= 60000) {
      meetinterval_ms = waarde;
    }
  }

  // Meting starten
  else if (commando == "START") {

    start_ms = millis();
    vorige_meting_ms = start_ms;
    if (pidIngesteld) {
      // Omgekeerde sensormontage: sensorhoek neemt toe bij optillen.
      werkhoek = meetHoek() - beginhoek;
      if (werkhoek > 180) werkhoek -= 360;
      if (werkhoek < -180) werkhoek += 360;
      if (!controleerMaxHoek()) return;
      stopPID();
      regelaar.SetMode(AUTOMATIC);
      pidActief = true;
      Serial.println("STARTED");
    }
    meten = true;
    laatste_heartbeat_ms = millis();
  }

  // Meting stoppen
  else if (commando == "STOP") {

    meten = false;
    stopPID();
    pidIngesteld = false;
    stelPWMIn(0);
  }
}

// Seriële communicatie zonder blokkerende readStringUntil()
void leesSerieel() {

  while (Serial.available() > 0) {

    char teken = Serial.read();

    if (teken == '\n') {

      verwerkCommando(invoer);
      invoer = "";

    } else if (teken != '\r') {

      if (invoer.length() < 180) {
        invoer += teken;
      } else {
        invoer = "";
      }
    }
  }
}

// ==========================================
// 4. SETUP
// ==========================================

void setup() {

  Wire.begin();
  sensor.begin();

  pinMode(enablePin, OUTPUT);
  pinMode(motorPin1, OUTPUT);
  pinMode(motorPin2, OUTPUT);

  digitalWrite(motorPin1, LOW);
  digitalWrite(motorPin2, HIGH);

  analogWrite(enablePin, 0);

  Serial.begin(115200);

  laatste_heartbeat_ms = millis();
}

// ==========================================
// 5. LOOP
// ==========================================

void loop() {

  // A. Verwerk commando's vanuit Python
  leesSerieel();

  // Lees de tijd na commando's die de heartbeat kunnen bijwerken.
  unsigned long tijd = millis();

  // B. Watchdog
  if (tijd - laatste_heartbeat_ms > watchdog_ms) {

    if (pwm != 0) {
      Serial.println("DEBUG_WATCHDOG");
    }

    stelPWMIn(0);
    stopPID();
    meten = false;
  }

  if (meten && pidActief && !continu && tijd - start_ms >= meetduur_ms) {
    meten = false; stopPID();
    pwm = 0; analogWrite(enablePin, 0);
    Serial.println("DONE");
  }

  // C. Hoekmetingen
  if (meten && tijd - vorige_meting_ms >= meetinterval_ms) {

    vorige_meting_ms = tijd;

    float hoek = meetHoek();

    if (pidActief) {
      werkhoek = hoek - beginhoek;
      if (werkhoek > 180) werkhoek -= 360;
      if (werkhoek < -180) werkhoek += 360;
      if (!controleerMaxHoek()) return;
      if (maxPWM > 0) regelaar.Compute();
      else pidPWM = 0;
      pwm = (int)pidPWM;
      analogWrite(enablePin, pwm);
      Serial.print(tijd - start_ms); Serial.print(',');
      Serial.print(doelhoek, 3); Serial.print(',');
      Serial.print(werkhoek, 3); Serial.print(','); Serial.println(pwm);
      return;
    }
    Serial.print(tijd);
    Serial.print(",");
    Serial.println(hoek, 3);
  }
}
