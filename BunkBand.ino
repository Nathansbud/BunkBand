#include <HCSR04.h>
#define NUM_SENSORS 2

// HCSR04 sensors(7, new int[2]{11, 12}, 2); //new int[4]{9, 10, 11, 12}, 4);

void setup() {
  Serial.begin(115200);
}

void loop() {
  // Hardcoding sensor readings
  for(int i = 0; i < NUM_SENSORS; i++) {
    Serial.print(i);
    Serial.print("-");
    Serial.println(random(0, 80));
  }

  /* Preliminary setup for simply reading all the sensors */
  // for(int i = 0; i < NUM_SENSORS; i++) {
  //   Serial.print(i);
  //   Serial.print("] Sensor Reading: ");
  //   Serial.println(sensors.dist(i)); 
  // }

  delay(50);
}