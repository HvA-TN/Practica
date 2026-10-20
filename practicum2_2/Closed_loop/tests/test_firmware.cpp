// Compiles the actual sketch and PID_v1 against simulated hardware.
#include "stubs/Arduino.h"
#include "stubs/Wire.h"
#include <cassert>
#include <iostream>
unsigned long fakeTime = 0;
int motorPWM = 0, sensorRaw = 1024, magnetStatus = 0x20;
bool sensorConnected = true;
MockSerial Serial;
MockWire Wire;
#include "../arduino/PID_Python_aansturing/PID_Python_aansturing.ino"

void command(const std::string &text) {
  Serial.outgoing.clear();
  Serial.incoming = text + "\n";
  while (Serial.available()) loop();
}

int main() {
  setup();
  assert(motorPWM == 0 && !measuring);
  command("START");
  assert(Serial.outgoing == "ERROR:NOT_CONFIGURED\n");
  command("HELLO");
  assert(Serial.outgoing == "PID_READY\n");
  command("CONFIG:40,2,0,0,60,1000");
  assert(Serial.outgoing == "CONFIG_OK\n");
  command("START");
  assert(measuring && regulating && motorPWM == 60); // P output clamped.
  fakeTime += 1000; loop();
  assert(!measuring && motorPWM == 0);
  assert(Serial.outgoing.find("DONE\n") != std::string::npos);
  command("CHECK");
  assert(measuring && !regulating && motorPWM == 0);
  fakeTime += 20; loop();
  assert(motorPWM == 0);
  command("STOP");
  assert(!measuring && motorPWM == 0);
  command("CONFIG:40,2,0,0,60,10000");
  command("START");
  fakeTime += 2500;
  command("PING"); // Updated heartbeat must not cause unsigned underflow.
  assert(measuring);
  fakeTime += 3001; loop();
  assert(!measuring && motorPWM == 0);
  assert(Serial.outgoing.find("ERROR:WATCHDOG\n") != std::string::npos);
  command("START");
  sensorConnected = false;
  fakeTime += 20; loop();
  assert(!measuring && motorPWM == 0);
  sensorConnected = true;
  sensorRaw = 0; // 90 degrees is outside allowed angle range.
  command("START");
  assert(Serial.outgoing == "ERROR:SENSOR_OR_ANGLE\n");
  sensorRaw = 1024;
  for (const auto &bad : {"CONFIG:nan,2,0,0,60,1000",
                         "CONFIG:40,2,0,0,121,1000",
                         "CONFIG:40,-2,0,0,60,1000",
                         "CONFIG:40,2,0,0,60,1000,extra"}) {
    command(bad);
    assert(!configured && !measuring && motorPWM == 0);
    command("START");
    assert(Serial.outgoing == "ERROR:NOT_CONFIGURED\n");
  }
  command("CONFIG:40,2,1,0,60,10000");
  command("START");
  fakeTime += 100; loop();
  command("STOP");
  command("CONFIG:0,0,1,0,60,10000");
  command("START");
  fakeTime += 20; loop();
  assert(motorPWM == 0); // Previous integrator was cleared.
  command(std::string(180, 'a'));
  assert(!measuring && motorPWM == 0);
  std::cout << "Firmware simulation passed\n";
}
