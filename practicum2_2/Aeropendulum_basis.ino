#include <Wire.h>P{}
#include <AS5600.h>

AS5600  as5600;  //create sensor object

unsigned long currentMs;  //current time variable
unsigned long lastMs;     // time of last measurement
const unsigned int FREE_RUN_PERIOD_MS = 5; //sampling period in milliseconds
double sig_angle_deg;  // angle measurement

void readAndPrintAngle();

void setup() {

  Wire.begin();     // Initialize I2C
  as5600.begin();   // Initialize sensor
  lastMs= millis();   // Initialize timing
  Serial.begin(9600);  // Initialize Serial Monitor
  delay(2000);
  Serial.print("Test: ");
  Serial.println();
}


void loop() {
  // Read and print the angle from AS5600 at the sampling frequency
  currentMs = millis();
  if (currentMs - lastMs >= FREE_RUN_PERIOD_MS) {// periodic sampling

    readAndPrintAngle();

    // Print the angle to the Serial Monitor
    Serial.print(sig_angle_deg);
    Serial.print(" ");
 
  }
}

void readAndPrintAngle() {
      lastMs = currentMs;
      sig_angle_deg = (float)as5600.readAngle()*0.0879; //0.0879=360/4096;  // degrees [0..360) 
}
