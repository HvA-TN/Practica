
#include <Wire.h>
#include <AS5600.h>

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

unsigned long meetinterval_ms = 100;
unsigned long vorige_meting_ms = 0;

unsigned long laatste_heartbeat_ms = 0;
const unsigned long watchdog_ms = 3000;

bool meten = false;

// Buffer voor seriële commando's
String invoer = "";

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

      stelPWMIn(waarde);
      laatste_heartbeat_ms = millis();
    }
  }

  // Meetinterval instellen
  else if (commando.startsWith("DT:")) {

    unsigned long waarde = commando.substring(3).toInt();

    if (waarde >= 10 && waarde <= 60000) {
      meetinterval_ms = waarde;
    }
  }

  // Meting starten
  else if (commando == "START") {

    vorige_meting_ms = millis();
    meten = true;
    laatste_heartbeat_ms = millis();
  }

  // Meting stoppen
  else if (commando == "STOP") {

    meten = false;
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

      if (invoer.length() < 40) {
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
    meten = false;
  }

  // C. Hoekmetingen
  if (meten && tijd - vorige_meting_ms >= meetinterval_ms) {

    vorige_meting_ms = tijd;

    float hoek = meetHoek();

    Serial.print(tijd);
    Serial.print(",");
    Serial.println(hoek, 3);
  }
}
