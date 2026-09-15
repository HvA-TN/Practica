#include <Wire.h>
#include <PID_v1.h>
#include <AS5600.h>

AS5600  as5600;  //create sensor object

unsigned long currentMs;  //current time variable
unsigned long lastMs;     // time of last measurement
const unsigned int FREE_RUN_PERIOD_MS = 5; //sampling period in milliseconds
double sig_angle_deg;  // angle measurement
double sig_angle_real; //actual angle 

// Motor control pins
const int motorPin1 = 10; // IN1
const int motorPin2 = 11; // IN2
const int enablePin = 9; // ENA (PWM pin for speed control)


double setpoint = 40; // Desired angle (vertical position)
double output = 0;

// PID parameters
double Kp = 2;
double Ki = 0.5;
double Kd = 0;
PID myPID(&sig_angle_real, &output, &setpoint, Kp, Ki, Kd, DIRECT);

void readAndPrintAngle();

void setup() {
  // Set motor control pins as outputs
  pinMode(motorPin1, OUTPUT);
  pinMode(motorPin2, OUTPUT);
  pinMode(enablePin, OUTPUT);

  Wire.begin();     // Initialize I2C
  as5600.begin();   // Initialize sensor
  lastMs= millis();   // Initialize timing
  Serial.begin(9600);  // Initialize Serial Monitor
  delay(2000);
  Serial.print("Test: ");
  Serial.println();

  // Initialize PID controller
  myPID.SetMode(AUTOMATIC);
  myPID.SetSampleTime(FREE_RUN_PERIOD_MS); // Set sample time in milliseconds
  myPID.SetOutputLimits(0,255);
}

void loop() {
  // Read and print the angle from AS5600 at the sampling frequency
  currentMs = millis();
  if (currentMs - lastMs >= FREE_RUN_PERIOD_MS) {// periodic sampling

    readAndPrintAngle();

    sig_angle_real = 90 - sig_angle_deg ;

    myPID.Compute(); // Calculate PID output

    // Set motor direction based on PID output
    if (output > 0) {
      digitalWrite(motorPin1, LOW);
      digitalWrite(motorPin2, HIGH);
    } else {
      digitalWrite(motorPin1, HIGH);
      digitalWrite(motorPin2, LOW);
    }

    analogWrite(enablePin, abs(output));

    // Print the angle to the Serial Monitor
    Serial.print(sig_angle_real);
    Serial.print(" ");
    // Print PID output for debugging
    Serial.println(output);
 
  }
}

void readAndPrintAngle() {
      lastMs = currentMs;
      sig_angle_deg = (float)as5600.readAngle()*0.0879; //0.0879=360/4096;  // degrees [0..360) 
}
