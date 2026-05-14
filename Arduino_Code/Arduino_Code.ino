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


// Поточні стани виходів для уникнення зайвих дубльованих записів
bool leftState      = false;
bool rightState     = false;
bool emergencyState = false;
bool brakeState     = false;


// Неблокуючий serial buffer
static char serialBuffer[32];
static uint8_t serialPos = 0;



void setup() {
  Serial.begin(115200);
  Serial.setTimeout(10);

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



void handleCommand(const String& cmd) {
  if (cmd.length() == 0) return;

  // SPEED:0-100
  if (cmd.startsWith("SPEED:")) {
    int pct = cmd.substring(6).toInt();
    pct = constrain(pct, 0, 100);

    if (pct <= 0) {
      targetServoSpeed = SERVO_STOP;
    } else {
      targetServoSpeed = map(pct, 1, 100, SERVO_MIN_MOVE, SERVO_MAX);
    }

    currentCommand = cmd;
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
    bool newState = (state == 1);

    if (signal == "ALARM") {
      alarmActive = newState;
      if (!alarmActive) {
        noTone(BUZZER_PIN);
        beepState = false;
      }
    }
    else if (signal == "LEFT") {
      if (leftState != newState) {
        leftState = newState;
        digitalWrite(LED_LEFT, leftState ? HIGH : LOW);
      }
    }
    else if (signal == "RIGHT") {
      if (rightState != newState) {
        rightState = newState;
        digitalWrite(LED_RIGHT, rightState ? HIGH : LOW);
      }
    }
    else if (signal == "EMERGENCY") {
      if (emergencyState != newState) {
        emergencyState = newState;
        digitalWrite(LED_EMERGENCY, emergencyState ? HIGH : LOW);
      }
    }
    else if (signal == "BRAKE") {
      if (brakeState != newState) {
        brakeState = newState;
        digitalWrite(LED_BRAKE, brakeState ? HIGH : LOW);
      }
    }

    currentCommand = cmd;
    Serial.print("OK: ");
    Serial.println(cmd);
  }
  // Старі текстові команди (fallback)
  else if (cmd == "STOP") {
    currentCommand = cmd;
    targetServoSpeed = SERVO_STOP;
    Serial.println("OK: STOP");
  }
  else if (cmd == "FULL") {
    currentCommand = cmd;
    targetServoSpeed = SERVO_MAX;
    Serial.println("OK: FULL");
  }
}



void readSerialCommand() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();

    if (c == '\r') {
      continue;
    }

    if (c == '\n') {
      serialBuffer[serialPos] = '\0';
      String cmd = String(serialBuffer);
      cmd.trim();
      serialPos = 0;
      handleCommand(cmd);
      continue;
    }

    if (serialPos < sizeof(serialBuffer) - 1) {
      serialBuffer[serialPos++] = c;
    } else {
      // overflow protection: скидаємо буфер
      serialPos = 0;
    }
  }
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