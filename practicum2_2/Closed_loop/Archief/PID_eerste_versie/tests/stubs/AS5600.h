#pragma once
#include "Arduino.h"
#define AS5600_OK 0
extern bool sensorConnected;
extern int sensorRaw, magnetStatus;
struct AS5600 {
  void begin() {}
  int lastError() { return 0; }
  bool isConnected() { return sensorConnected; }
  byte readStatus() { return magnetStatus; }
  int readAngle() { return sensorRaw; }
};
