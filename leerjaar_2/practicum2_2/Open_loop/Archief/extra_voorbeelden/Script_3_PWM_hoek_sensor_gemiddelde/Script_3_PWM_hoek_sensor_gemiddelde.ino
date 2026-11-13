
#include <Wire.h>
#include <AS5600.h>
#include <math.h>

// =====================================================
// 1. INSTELLINGEN
// =====================================================

// PWM-sweep
const int pwm_start = 60;
const int pwm_eind = 120;
const int pwm_stap = 10;

// Tijd per PWM-instelling (10 seconden)
const unsigned long meetduur_ms = 10000;

// Meetinterval (100 ms = 10 Hz)
const unsigned long meetinterval_ms = 100;

// Omrekening AS5600 naar graden
const float graden_per_stap = 360.0 / 4096.0;

// =====================================================
// 2. PINNEN EN VARIABELEN
// =====================================================

// H-brug L298N
const int enablePin = 9;
const int motorPin1 = 10;
const int motorPin2 = 11;

// Hoeksensor
AS5600 sensor;

// Huidige PWM-instelling
int pwm_waarde = pwm_start;

// Tijdregistratie
unsigned long start_periode_ms = 0;
unsigned long vorige_meting_ms = 0;

// Statistische variabelen
unsigned int aantal_metingen = 0;

double som_hoek = 0.0;
double som_hoek_kwadraat = 0.0;

// Status van de sweep
bool sweep_klaar = false;

// =====================================================
// 3. SETUP
// =====================================================

void setup() {

  // Initialiseer hoeksensor
  Wire.begin();
  sensor.begin();

  // Configureer motorpinnen
  pinMode(enablePin, OUTPUT);
  pinMode(motorPin1, OUTPUT);
  pinMode(motorPin2, OUTPUT);

  // Motor uit
  analogWrite(enablePin, 0);

  // Stel draairichting in
  digitalWrite(motorPin1, LOW);
  digitalWrite(motorPin2, HIGH);

  // Seriële communicatie
  Serial.begin(115200);

  delay(2000);

  // Start de eerste meetperiode
  start_periode_ms = millis();
  vorige_meting_ms = start_periode_ms;

  // Start de motor
  analogWrite(enablePin, pwm_waarde);

  // Kolomnamen voor de meetresultaten
  Serial.println("PWM,gemiddelde_deg,STD_deg,N");
}

// =====================================================
// 4. LOOP
// =====================================================

void loop() {

  // Stop wanneer alle PWM-waarden zijn doorlopen
  if (sweep_klaar) {
    return;
  }

  unsigned long huidige_tijd_ms = millis();

  // -----------------------------------------------
  // A. CONTROLEER EINDE MEETPERIODE
  // -----------------------------------------------

  if (huidige_tijd_ms - start_periode_ms >= meetduur_ms) {

    // Bereken en print het resultaat
    verwerkMeetperiode();

    // Ga naar de volgende PWM-waarde
    pwm_waarde += pwm_stap;

    // Controleer of de sweep klaar is
    if (pwm_waarde > pwm_eind) {

      // Zet de motor uit
      analogWrite(enablePin, 0);

      sweep_klaar = true;
      return;
    }

    // Reset statistische variabelen
    aantal_metingen = 0;
    som_hoek = 0.0;
    som_hoek_kwadraat = 0.0;

    // Start nieuwe periode
    start_periode_ms = millis();
    vorige_meting_ms = start_periode_ms;

    // Stel nieuwe PWM-waarde in
    analogWrite(enablePin, pwm_waarde);
  }

  // -----------------------------------------------
  // B. HOEKMETING
  // -----------------------------------------------

  huidige_tijd_ms = millis();

  if (huidige_tijd_ms - vorige_meting_ms >= meetinterval_ms) {

    vorige_meting_ms = huidige_tijd_ms;

    // Lees de AS5600
    int ruwe_hoek = sensor.readAngle();

    // Reken om naar graden
    double hoek_graden = ruwe_hoek * graden_per_stap;

    // Verzamel gegevens voor de statistiek
    aantal_metingen++;

    som_hoek += hoek_graden;

    som_hoek_kwadraat += hoek_graden * hoek_graden;
  }
}

// =====================================================
// 5. VERWERK MEETPERIODE
// =====================================================

void verwerkMeetperiode() {

  // Controleer of er metingen beschikbaar zijn
  if (aantal_metingen < 2) {
    return;
  }

  // -----------------------------------------------
  // A. GEMIDDELDE
  // -----------------------------------------------

  double gemiddelde = som_hoek / aantal_metingen;

  // -----------------------------------------------
  // B. STANDAARDAFWIJKING
  // -----------------------------------------------

  double variantie =
      (som_hoek_kwadraat
       - aantal_metingen * gemiddelde * gemiddelde)
      / (aantal_metingen - 1);

  // Voorkom negatieve variantie door afrondfouten
  if (variantie < 0) {
    variantie = 0;
  }

  double standaardafwijking = sqrt(variantie);

  // -----------------------------------------------
  // C. RESULTATEN
  // -----------------------------------------------

  Serial.print(pwm_waarde);
  Serial.print(",");

  Serial.print(gemiddelde, 3);
  Serial.print(",");

  Serial.print(standaardafwijking, 3);
  Serial.print(",");

  Serial.println(aantal_metingen);
}
