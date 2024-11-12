#include <HCSR04.h>
#define NUM_SENSORS 1

HCSR04 sensors(3, 2);

void setup() {
  Serial.begin(9600);
}

void loop() {
  // Hardcoding sensor readings
  for(int i = 0; i < NUM_SENSORS; i++) {
    Serial.print(i);
    Serial.print("-");
    Serial.println(sensors.dist(i)); 
    // Serial.println(random(0, 80));
  }

  delay(50);
}