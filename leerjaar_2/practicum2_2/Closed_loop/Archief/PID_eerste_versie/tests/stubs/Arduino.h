#pragma once
#include <string>
#include <sstream>
#include <iomanip>
using byte = unsigned char;
#define OUTPUT 1
#define LOW 0
#define HIGH 1
extern unsigned long fakeTime;
extern int motorPWM;
inline unsigned long millis() { return fakeTime; }
inline void pinMode(int, int) {}
inline void digitalWrite(int, int) {}
inline void analogWrite(int, int pwm) { motorPWM = pwm; }
struct MockSerial {
  std::string incoming, outgoing;
  void begin(int) {}
  int available() { return (int)incoming.size(); }
  char read() { char c = incoming[0]; incoming.erase(0, 1); return c; }
  template<class T> void print(T value) {
    std::ostringstream s; s << value; outgoing += s.str();
  }
  void print(double value, int digits) {
    std::ostringstream s; s << std::fixed << std::setprecision(digits) << value;
    outgoing += s.str();
  }
  template<class T> void println(T value) { print(value); outgoing += "\n"; }
};
extern MockSerial Serial;
