// PID op de Arduino; instellingen en meetgegevens via Python (115200 baud).
#include <Wire.h>
#include <AS5600.h>
#include <PID_v1.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

// 1. Hardware en grenzen: controleren voor jouw opstelling.
const int enablePin = 9, motorPin1 = 10, motorPin2 = 11;
const int MAX_PWM = 120;  // Python kan een lagere grens kiezen.
const double ANGLE_OFFSET_DEG = 90;
const double MIN_ANGLE_DEG = -10, MAX_ANGLE_DEG = 80;
const unsigned long SAMPLE_MS = 20, WATCHDOG_MS = 3000;

AS5600 sensor;
double angle = 0, output = 0, setpoint = 40;
PID controller(&angle, &output, &setpoint, 2, 0, 0, DIRECT);

// 2. Status van de meting.
bool configured = false, measuring = false, regulating = false;
unsigned long durationMs = 30000, startTime = 0, lastSample = 0;
unsigned long lastHeartbeat = 0;
char input[160];
unsigned int inputLength = 0;
bool overflow = false;

// 3. Motor en sensor.
void stopMotor() {
  analogWrite(enablePin, 0);
  controller.SetMode(MANUAL);
  output = 0;
  measuring = false;
  regulating = false;
}

void fail(const char *reason) {
  stopMotor();
  Serial.print("ERROR:");
  Serial.println(reason);
}

bool readAngle() {
  sensor.lastError();
  if (!sensor.isConnected()) return false;
  byte status = sensor.readStatus();
  if (sensor.lastError() != AS5600_OK || (status & 0x38) != 0x20) return false;
  angle = ANGLE_OFFSET_DEG - sensor.readAngle() * (360.0 / 4096.0);
  return sensor.lastError() == AS5600_OK &&
         angle >= MIN_ANGLE_DEG && angle <= MAX_ANGLE_DEG;
}

// 4. Commando's: HELLO, CONFIG, START, CHECK, PING en STOP.
// CONFIG:doelhoek,kp,ki,kd,max_pwm,meetduur_ms
void configure(char *text) {
  configured = false;
  double values[6];
  char *next = text;
  for (int i = 0; i < 6; i++) {
    char *end;
    values[i] = strtod(next, &end);
    if (end == next || !isfinite(values[i]) ||
        (i < 5 ? *end != ',' : *end != '\0')) {
      fail("CONFIG"); return;
    }
    next = end + 1;
  }
  if (values[0] < MIN_ANGLE_DEG || values[0] > MAX_ANGLE_DEG ||
      values[1] < 0 || values[1] > 1000 ||
      values[2] < 0 || values[2] > 1000 ||
      values[3] < 0 || values[3] > 1000 ||
      values[4] < 1 || values[4] > MAX_PWM || values[4] != floor(values[4]) ||
      values[5] < 20 || values[5] > 600000 || values[5] != floor(values[5])) {
    fail("CONFIG"); return;
  }
  setpoint = values[0];
  controller.SetTunings(values[1], values[2], values[3]);
  controller.SetOutputLimits(0, values[4]);
  durationMs = (unsigned long)values[5];
  configured = true;
  Serial.println("CONFIG_OK");
}

void processCommand(char *command) {
  if (strcmp(command, "STOP") == 0) {
    stopMotor();
    Serial.println("STOPPED");
  } else if (strcmp(command, "PING") == 0) {
    lastHeartbeat = millis();
  } else if (strcmp(command, "HELLO") == 0) {
    stopMotor();
    Serial.println("PID_READY");
  } else if (strncmp(command, "CONFIG:", 7) == 0) {
    if (measuring) { fail("BUSY"); return; }
    configure(command + 7);
  } else if (strcmp(command, "START") == 0 || strcmp(command, "CHECK") == 0) {
    if (measuring) { fail("BUSY"); return; }
    if (!configured) { fail("NOT_CONFIGURED"); return; }
    if (!readAngle()) { fail("SENSOR_OR_ANGLE"); return; }
    stopMotor();
    regulating = strcmp(command, "START") == 0;
    // MANUAL -> AUTOMATIC initialiseert de integrator met output = 0.
    if (regulating) controller.SetMode(AUTOMATIC);
    startTime = millis();
    lastHeartbeat = startTime;
    lastSample = startTime - SAMPLE_MS;
    measuring = true;
    Serial.println("STARTED");
  } else {
    fail("COMMAND");
  }
}

void readSerial() {
  // Beperk het werk per loop, zodat de regeling aan de beurt blijft.
  for (int n = 0; n < 64 && Serial.available() > 0; n++) {
    char c = Serial.read();
    if (c == '\n') {
      if (overflow) {
        fail("COMMAND_TOO_LONG");
      } else {
        input[inputLength] = '\0';
        processCommand(input);
      }
      inputLength = 0;
      overflow = false;
    } else if (c != '\r') {
      if (inputLength < sizeof(input) - 1 && !overflow) input[inputLength++] = c;
      else overflow = true;
    }
  }
}

// 5. Opstarten en regelkring.
void setup() {
  pinMode(enablePin, OUTPUT);
  pinMode(motorPin1, OUTPUT);
  pinMode(motorPin2, OUTPUT);
  digitalWrite(motorPin1, LOW);
  digitalWrite(motorPin2, HIGH);
  stopMotor();
  Wire.begin();
  sensor.begin();
  controller.SetSampleTime(SAMPLE_MS);
  controller.SetOutputLimits(0, MAX_PWM);
  Serial.begin(115200);
}

void loop() {
  readSerial();
  unsigned long now = millis();  // Na het verwerken van de heartbeat.
  if (!measuring) return;
  if (now - lastHeartbeat > WATCHDOG_MS) { fail("WATCHDOG"); return; }
  if (now - startTime >= durationMs) {
    stopMotor();
    Serial.println("DONE");
    return;
  }
  if (now - lastSample < SAMPLE_MS) return;
  lastSample = now;
  if (!readAngle()) { fail("SENSOR_OR_ANGLE"); return; }
  if (regulating) {
    controller.Compute();
    analogWrite(enablePin, (int)output);
  }
  // Milliseconden sinds START/CHECK, doelhoek, werkhoek, aangeboden PWM.
  Serial.print(now - startTime); Serial.print(',');
  Serial.print(setpoint, 3); Serial.print(',');
  Serial.print(angle, 3); Serial.print(',');
  Serial.println((int)output);
}
