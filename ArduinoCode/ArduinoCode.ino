#include <Servo.h>

Servo motor;

const int SERVO_PIN = 9;
const int BUZZER_PIN = 8;

const int LED_LEFT      = 2;
const int LED_RIGHT     = 3;
const int LED_EMERGENCY = 4;
const int LED_BRAKE     = 5;

const int SERVO_STOP = 92;
const int SERVO_FULL = 180;
const int SERVO_SLOW = 120;

String currentCommand = "STOP";
int currentServoSpeed = SERVO_STOP;

const int SERVO_STEP = 2;
const int SERVO_DELAY = 20;

bool alarmActive = false;
unsigned long lastBeepTime = 0;
bool beepState = false;
unsigned long lastServoTime = 0;

void setup() {
  Serial.begin(9600);

  motor.attach(SERVO_PIN);
  motor.write(SERVO_STOP);

  pinMode(BUZZER_PIN,    OUTPUT);
  pinMode(LED_LEFT,      OUTPUT);
  pinMode(LED_RIGHT,     OUTPUT);
  pinMode(LED_EMERGENCY, OUTPUT);
  pinMode(LED_BRAKE,     OUTPUT);

  digitalWrite(LED_LEFT,      LOW);
  digitalWrite(LED_RIGHT,     LOW);
  digitalWrite(LED_EMERGENCY, LOW);
  digitalWrite(LED_BRAKE,     LOW);

  Serial.println("Система готова");
}

void loop() {
  readSerialCommand();
  updateServo();
  updateAlarm();
}

void readSerialCommand() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "FULL" || cmd == "SLOW" || cmd == "STOP") {
      currentCommand = cmd;
      Serial.print("OK: ");
      Serial.println(currentCommand);
    }
    else if (cmd.indexOf(':') != -1) {
      String signal = cmd.substring(0, cmd.indexOf(':'));
      int state     = cmd.substring(cmd.indexOf(':') + 1).toInt();

      if (signal == "ALARM") {
        alarmActive = (state == 1);
        if (!alarmActive) {
          noTone(BUZZER_PIN);
          beepState = false;
        }
        Serial.print("OK: ALARM:");
        Serial.println(state);
      }
      else if (signal == "LEFT") {
        digitalWrite(LED_LEFT, state ? HIGH : LOW);
        Serial.print("OK: LEFT:");
        Serial.println(state);
      }
      else if (signal == "RIGHT") {
        digitalWrite(LED_RIGHT, state ? HIGH : LOW);
        Serial.print("OK: RIGHT:");
        Serial.println(state);
      }
      else if (signal == "EMERGENCY") {
        digitalWrite(LED_EMERGENCY, state ? HIGH : LOW);
        Serial.print("OK: EMERGENCY:");
        Serial.println(state);
      }
      else if (signal == "BRAKE") {
        digitalWrite(LED_BRAKE, state ? HIGH : LOW);
        Serial.print("OK: BRAKE:");
        Serial.println(state);
      }
    }
  }
}

void updateAlarm() {
  if (!alarmActive) return;

  unsigned long now = millis();
  if (now - lastBeepTime >= 150) {
    lastBeepTime = now;
    beepState = !beepState;
    if (beepState) {
      tone(BUZZER_PIN, 2000);
    } else {
      noTone(BUZZER_PIN);
    }
  }
}

void updateServo() {
  unsigned long now = millis();
  if (now - lastServoTime < SERVO_DELAY) return;
  lastServoTime = now;

  int targetSpeed = SERVO_FULL;
  if (currentCommand == "SLOW") targetSpeed = SERVO_SLOW;
  else if (currentCommand == "STOP") targetSpeed = SERVO_STOP;

  if (currentServoSpeed < targetSpeed) currentServoSpeed += SERVO_STEP;
  else if (currentServoSpeed > targetSpeed) currentServoSpeed -= SERVO_STEP;

  motor.write(currentServoSpeed);
}
