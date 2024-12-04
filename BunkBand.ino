#include <HCSR04.h>
#define NUM_SENSORS 4

HCSR04 sensors[4] = {
  HCSR04(12, 13),
  HCSR04(10, 11),
  HCSR04(8, 9),
  HCSR04(6, 7)
};

void setup() {
  Serial.begin(9600);
}

void loop() {
  // Hardcoding sensor readings
  for(int i = 0; i < NUM_SENSORS; i++) {
    Serial.print(i);
    Serial.print("-");
    Serial.println(sensors[i].dist()); 
  }

  delay(50);
}