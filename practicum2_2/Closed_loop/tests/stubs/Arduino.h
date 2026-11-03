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
  void println(double v, int d) { print(v, d); outgoing += "\n"; }
  template<class T> void println(T value) { print(value); outgoing += "\n"; }
};
extern MockSerial Serial;

#include <cstdlib>
#include <cctype>
class String : public std::string {
public:
 using std::string::string;
 String(const std::string &s): std::string(s) {}
 void trim() { auto a=find_first_not_of(" \r\n\t"); if(a==npos) clear(); else *this=substr(a,find_last_not_of(" \r\n\t")-a+1); }
 bool startsWith(const char *s) const { return find(s)==0; }
 String substring(size_t n) const { return substr(n); }
 long toInt() const { return std::strtol(c_str(), nullptr, 10); }
};
inline bool isDigit(char c) { return std::isdigit((unsigned char)c); }
