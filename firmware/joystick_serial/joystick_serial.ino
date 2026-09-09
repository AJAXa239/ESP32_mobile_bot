const int PIN_Y = A1;   // forward / backward
const int PIN_X = A3;   // left / right
const int PIN_BUTTON = 8;
const int PIN_ESTOP = 6;

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  pinMode(PIN_ESTOP, INPUT_PULLUP);
}

void loop() {
  int x = analogRead(PIN_X);       // 0-1023, center ~512, left/right
  int y = analogRead(PIN_Y);       // 0-1023, center ~512, forward/back
  int button = digitalRead(PIN_BUTTON); // 0 = pressed (pull-up), 1 = released
  int estop = digitalRead(PIN_ESTOP);   // 0 = pressed (pull-up), 1 = released

  Serial.print(x);
  Serial.print(",");
  Serial.print(y);
  Serial.print(",");
  Serial.print(button);
  Serial.print(",");
  Serial.println(estop);

  delay(20); // 50Hz
}
