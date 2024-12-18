#include <Servo.h>

Servo myservo;
int tempo = 0;
unsigned long delay_len = 500;

void setup() {
  Serial.begin(9600);
  myservo.attach(5);
  myservo.write(0);
}
void loop() {
  if (Serial.available() > 2) {
    int x = Serial.parseInt();
    delay_len = (unsigned long) x;
  }
  delay(delay_len);
  myservo.write(20);
  delay(delay_len);
  myservo.write(0);
}
