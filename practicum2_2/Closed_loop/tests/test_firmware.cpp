#include "stubs/Arduino.h"
#include "stubs/Wire.h"
#include <cassert>
#include <iostream>
unsigned long fakeTime=0;
int motorPWM=0, sensorRaw=1024, magnetStatus=0x30;
bool sensorConnected=true;
MockSerial Serial;
MockWire Wire;
#include "../arduino/Stap_4_PID_Python_aansturing/Stap_4_PID_Python_aansturing.ino"
int main() {
 setup();
 verwerkCommando("PWM:0"); verwerkCommando("START");
 fakeTime=100; loop(); assert(motorPWM==0 && Serial.outgoing.find("90.000")!=std::string::npos);
 verwerkCommando("STOP"); verwerkCommando("HELLO"); verwerkCommando("OFFSET:90");
 verwerkCommando("CONFIG:40,2,0,0,60,1000,20,0,120"); assert(pidIngesteld);
 verwerkCommando("START"); fakeTime+=20; loop(); assert(motorPWM==60);
 fakeTime+=1000; loop(); assert(!meten && motorPWM==0);
 verwerkCommando("CONFIG:40,2,0,0,60,1000,20,1,120"); verwerkCommando("START");
 fakeTime+=1100; verwerkCommando("PING"); loop(); assert(meten && pidActief);
 fakeTime+=3001; loop(); assert(!meten && motorPWM==0);
 verwerkCommando("CONFIG:40,2,0,0,256,1000,20,0,120"); assert(!pidIngesteld);
 verwerkCommando("OFFSET:89"); sensorRaw=0;
 verwerkCommando("CONFIG:120,20,0,0,255,1000,20,0,120"); assert(pidIngesteld);
 verwerkCommando("START"); fakeTime+=20; loop();
 assert(werkhoek==89 && motorPWM==255);
 verwerkCommando("STOP");
 verwerkCommando("CONFIG:-120,2,0,0,0,1000,20,0,120"); assert(pidIngesteld);
 verwerkCommando("START"); fakeTime+=20; loop(); assert(motorPWM==0);
 verwerkCommando("STOP");
 verwerkCommando("CONFIG:120,20,0,0,0,1000,20,0,120"); assert(pidIngesteld);
 verwerkCommando("START"); fakeTime+=20; loop(); assert(motorPWM==0);
 verwerkCommando("STOP");
 verwerkCommando("CONFIG:121,2,0,0,255,1000,20,0,120"); assert(!pidIngesteld);
 verwerkCommando("CONFIG:-181,2,0,0,255,1000,20,0,120"); assert(!pidIngesteld);
 verwerkCommando("CONFIG:40,2,0,0,-1,1000,20,0,120"); assert(!pidIngesteld);
 // Start above limit: refuse before powering motor.
 verwerkCommando("OFFSET:90"); sensorRaw=0;
 verwerkCommando("CONFIG:40,2,0,0,255,1000,20,0,60");
 verwerkCommando("START"); assert(!meten && hoekStop && motorPWM==0);
 assert(Serial.outgoing.find("ERROR:MAX_HOEK")!=std::string::npos);
 verwerkCommando("PWM:100"); assert(motorPWM==0);
 // A valid new configuration resets the latch. At the limit is allowed.
 sensorRaw=1024;
 verwerkCommando("CONFIG:40,2,0,0,255,1000,20,0,45");
 verwerkCommando("START"); fakeTime+=20; loop(); assert(motorPWM>0);
 sensorRaw=512; fakeTime+=20; loop(); assert(meten && werkhoek==45);
 sensorRaw=511; fakeTime+=20; loop();
 assert(!meten && !pidActief && hoekStop && motorPWM==0);
 sensorRaw=1024; fakeTime+=20; loop(); assert(motorPWM==0);
 verwerkCommando("START"); assert(!meten && motorPWM==0);
 verwerkCommando("CONFIG:60,2,0,0,255,1000,20,0,45"); assert(!pidIngesteld);
 // Above 120 degrees remains allowed until the configured 150-degree limit.
 verwerkCommando("OFFSET:180"); sensorRaw=1024;
 verwerkCommando("CONFIG:140,2,0,0,255,1000,20,0,150"); assert(pidIngesteld);
 verwerkCommando("START"); fakeTime+=20; loop(); assert(meten && motorPWM>0);
 sensorRaw=512; fakeTime+=20; loop(); assert(meten && werkhoek==135);
 sensorRaw=256; fakeTime+=20; loop(); assert(!meten && motorPWM==0 && hoekStop);
 verwerkCommando("CONFIG:180,2,0,0,255,1000,20,0,180"); assert(pidIngesteld && maxHoek==180);
 verwerkCommando("CONFIG:-180,2,0,0,255,1000,20,0,-180"); assert(pidIngesteld && maxHoek==-180);
 verwerkCommando("START"); assert(!meten && motorPWM==0);
 verwerkCommando("CONFIG:40,2,0,0,255,1000,20,0,181"); assert(!pidIngesteld);
 verwerkCommando("CONFIG:-180,2,0,0,255,1000,20,0,-181"); assert(!pidIngesteld);
 std::cout << "Firmware simulation passed\n";
}
