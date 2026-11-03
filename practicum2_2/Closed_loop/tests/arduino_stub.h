
#pragma once
#include <string>
#include <cmath>
#include <cstdlib>
#include <cctype>
#include <cassert>
using std::isfinite; using byte=unsigned char;
const int OUTPUT=1,LOW=0,HIGH=1,DIRECT=0,MANUAL=0,AUTOMATIC=1;
unsigned long testTime=0; int motor=0; double testTarget=120;
unsigned long millis(){return testTime;}
void pinMode(int,int){} void digitalWrite(int,int){} void analogWrite(int,int v){motor=v;}
bool isDigit(char c){return std::isdigit(c);}
struct String{std::string s;String(const char*p=""):s(p){}String(std::string p):s(p){}
const char*c_str()const{return s.c_str();}unsigned int length()const{return s.size();}
char operator[](unsigned int i)const{return s[i];}void trim(){}
bool startsWith(const char*p)const{return s.rfind(p,0)==0;}
String substring(unsigned int n)const{return s.substr(n);}long toInt()const{return std::strtol(s.c_str(),nullptr,10);}
bool operator==(const char*p)const{return s==p;}String& operator+=(char c){s+=c;return *this;}};
struct SerialStub{void begin(int){}int available(){return 0;}char read(){return 0;}
template<class T>void print(T){}template<class T>void print(T,int){}
template<class T>void println(T){}template<class T>void println(T,int){}}Serial;
struct WireStub{void begin(){}}Wire;
struct AS5600{void begin(){}int lastError(){return 0;}int readAngle(){return 1024;}};
struct PID{double*out;double upper=255;PID(double*,double*o,double*,double,double,double,int):out(o){}
void SetMode(int){}void SetTunings(double,double,double){}void SetSampleTime(int){}
void SetOutputLimits(double,double hi){upper=hi;}void Compute(){*out=fmax(0.,fmin(upper,testTarget));}};
