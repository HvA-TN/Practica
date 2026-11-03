#pragma once
#include "Arduino.h"
struct MockWire { void begin() {} };
extern MockWire Wire;
