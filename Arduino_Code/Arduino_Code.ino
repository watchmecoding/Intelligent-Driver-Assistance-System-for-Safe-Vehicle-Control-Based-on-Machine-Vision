// ArduinoCode.ino
#include <Servo.h>

Servo motor;

const int SERVO_PIN = 9;
const int BUZZER_PIN = 8;

const int LED_LEFT      = 2;
const int LED_RIGHT     = 3;
const int LED_EMERGENCY = 4;
const int LED_BRAKE     = 5;

const int SERVO_STOP = 92;
const int SERVO_MIN_MOVE = 97;
const int SERVO_MAX  = 179;   // не 180, щоб не впиратись в упор

const int SERVO_STEP  = 2;
const int SERVO_DELAY = 20;

// Захист від перегріву: якщо серво на місці довше N мс — detach
const unsigned long SERVO_IDLE_TIMEOUT = 3000;

String currentCommand    = "STOP";
int    currentServoSpeed = SERVO_STOP;
int    targetServoSpeed  = SERVO_STOP;

bool          alarmActive   = false;
unsigned long lastBeepTime  = 0;
bool          beepState     = false;
unsigned long lastServoTime = 0;
unsigned long servoAtTargetSince = 0;
bool          servoDetached = false;


void setup() {
  Serial.begin(9600);

  motor.attach(SERVO_PIN);
  motor.write(SERVO_STOP);
  servoAtTargetSince = millis();

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
  if (!Serial.available()) return;

  String cmd = Serial.readStringUntil('\n');
  cmd.trim();

  // SPEED:0-100
  if (cmd.startsWith("SPEED:")) {
    int pct = cmd.substring(6).toInt();
    pct = constrain(pct, 0, 100);

    if (pct <= 0) {
      targetServoSpeed = SERVO_STOP;
    } else {
      targetServoSpeed = map(pct, 1, 100, SERVO_MIN_MOVE, SERVO_MAX);
    }

    servoAtTargetSince = 0;

    // Якщо серво було detach — перепідключаємо
    if (servoDetached) {
      motor.attach(SERVO_PIN);
      servoDetached = false;
    }

    Serial.print("OK: SPEED:");
    Serial.println(pct);
  }
  // Сигнали зі станом
  else if (cmd.indexOf(':') != -1) {
    String signal = cmd.substring(0, cmd.indexOf(':'));
    int    state  = cmd.substring(cmd.indexOf(':') + 1).toInt();

    if (signal == "ALARM") {
      alarmActive = (state == 1);
      if (!alarmActive) {
        noTone(BUZZER_PIN);
        beepState = false;
      }
    }
    else if (signal == "LEFT")      digitalWrite(LED_LEFT,      state ? HIGH : LOW);
    else if (signal == "RIGHT")     digitalWrite(LED_RIGHT,     state ? HIGH : LOW);
    else if (signal == "EMERGENCY") digitalWrite(LED_EMERGENCY, state ? HIGH : LOW);
    else if (signal == "BRAKE")     digitalWrite(LED_BRAKE,     state ? HIGH : LOW);

    Serial.print("OK: ");
    Serial.println(cmd);
  }
  // Старі текстові команди (fallback)
  else if (cmd == "STOP") { targetServoSpeed = SERVO_STOP; Serial.println("OK: STOP"); }
  else if (cmd == "FULL") { targetServoSpeed = SERVO_MAX;  Serial.println("OK: FULL"); }
}


void updateServo() {
  unsigned long now = millis();
  if (now - lastServoTime < SERVO_DELAY) return;
  lastServoTime = now;

  if (currentServoSpeed < targetServoSpeed)
    currentServoSpeed = min(currentServoSpeed + SERVO_STEP, targetServoSpeed);
  else if (currentServoSpeed > targetServoSpeed)
    currentServoSpeed = max(currentServoSpeed - SERVO_STEP, targetServoSpeed);

  // Серво досягло цілі
  if (currentServoSpeed == targetServoSpeed) {
    if (servoAtTargetSince == 0)
      servoAtTargetSince = now;

    // Якщо стоїть більше 3 сек на STOP — detach (знімає утримання)
    if (!servoDetached &&
        targetServoSpeed == SERVO_STOP &&
        now - servoAtTargetSince >= SERVO_IDLE_TIMEOUT) {
      motor.detach();
      servoDetached = true;
      Serial.println("INFO: servo detached (idle)");
    }
  } else {
    servoAtTargetSince = 0;
    if (servoDetached) {
      motor.attach(SERVO_PIN);
      servoDetached = false;
    }
  }

  if (!servoDetached)
    motor.write(currentServoSpeed);
}


void updateAlarm() {
  if (!alarmActive) return;

  unsigned long now = millis();
  if (now - lastBeepTime >= 333) {
    lastBeepTime = now;
    beepState = !beepState;
    beepState ? tone(BUZZER_PIN, 400) : noTone(BUZZER_PIN);
  }
}


// // Тест гучності пасивного динаміка
// const int BUZZER_PIN = 8;

// void setup() {
//     Serial.begin(9600);
//     Serial.println("Надсилай частоту (напр. 2500)");
// }

// void loop() {
//     if (Serial.available()) {
//         int freq = Serial.parseInt();
//         if (freq > 0) {
//             tone(BUZZER_PIN, freq);
//             Serial.print("Грає: ");
//             Serial.println(freq);
//         } else {
//             noTone(BUZZER_PIN);
//             Serial.println("Тиша");
//         }
//     }
// }