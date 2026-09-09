#include <micro_ros_arduino.h>
#include <WiFi.h>
#include <stdio.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <geometry_msgs/msg/twist.h>

// ---- Motor A (left) ----
int enA = 14;
int in1 = 27;
int in2 = 26;

// ---- Motor B (right) ----
int enB = 32;
int in3 = 25;
int in4 = 33;

// ---- PWM ----
const int freq = 1000;
const int pwmChannelA = 0;
const int pwmChannelB = 1;
const int resolution = 8;   // 0-255

// ---- WiFi / agent config ----
#define WIFI_SSID     ""
#define WIFI_PASSWORD ""
#define AGENT_IP      ""
#define AGENT_PORT    8888
#define WIFI_TIMEOUT_MS 15000

rcl_subscription_t twist_subscriber;
geometry_msgs__msg__Twist twist_msg;
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

unsigned long last_cmd_time = 0;
const unsigned long CMD_TIMEOUT_MS = 2000;
bool motors_timed_out = false;

#define RCCHECK(fn) { \
  rcl_ret_t temp_rc = fn; \
  if ((temp_rc != RCL_RET_OK)) { \
    Serial.print("RCCHECK FAILED at line "); \
    Serial.print(__LINE__); \
    Serial.print(" - rc = "); \
    Serial.println(temp_rc); \
    error_loop(); \
  } \
}

void stopMotors() {
  digitalWrite(in1, LOW);
  digitalWrite(in2, LOW);
  digitalWrite(in3, LOW);
  digitalWrite(in4, LOW);
  ledcWrite(enA, 0);
  ledcWrite(enB, 0);
}

void error_loop() {
  Serial.println("ERROR: RCL call failed - will retry init in 3s (motors stopped).");
  stopMotors();
  delay(3000);
  Serial.println("Retrying micro-ROS init...");
  ESP.restart();
}

void setMotor(int inA, int inB, int pwmPin, float value) {
  int duty = (int)(fabs(value) * 255.0);
  if (duty > 255) duty = 255;

  if (value > 0.05) {
    digitalWrite(inA, HIGH);
    digitalWrite(inB, LOW);
  } else if (value < -0.05) {
    digitalWrite(inA, LOW);
    digitalWrite(inB, HIGH);
  } else {
    digitalWrite(inA, LOW);
    digitalWrite(inB, LOW);
    duty = 0;
  }
  ledcWrite(pwmPin, duty);
}

void twist_callback(const void *msgin) {
  const geometry_msgs__msg__Twist *msg = (const geometry_msgs__msg__Twist *)msgin;
  float linear = msg->linear.x;
  float angular = msg->angular.z;

  float left = linear - angular;
  float right = linear + angular;

  if (left > 1.0) left = 1.0;
  if (left < -1.0) left = -1.0;
  if (right > 1.0) right = 1.0;
  if (right < -1.0) right = -1.0;

  Serial.print("cmd_vel linear=");
  Serial.print(linear);
  Serial.print(" angular=");
  Serial.print(angular);
  Serial.print(" -> left=");
  Serial.print(left);
  Serial.print(" right=");
  Serial.println(right);

  setMotor(in1, in2, enA, left);
  setMotor(in3, in4, enB, right);

  last_cmd_time = millis();
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("ESP32 teleop car starting...");

  pinMode(in1, OUTPUT);
  pinMode(in2, OUTPUT);
  pinMode(in3, OUTPUT);
  pinMode(in4, OUTPUT);

  ledcAttachChannel(enA, freq, resolution, pwmChannelA);
  ledcAttachChannel(enB, freq, resolution, pwmChannelB);

  stopMotors();

  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
    if (millis() - start > WIFI_TIMEOUT_MS) {
      Serial.println("\nWiFi FAILED to connect within timeout.");
      Serial.println("Halting safely (motors stopped). Check SSID/password/signal.");
      error_loop();
    }
  }
  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  // Disable WiFi power-saving/modem-sleep - it delays/buffers UDP packets
  // for many seconds at a time, causing exactly the "works then goes
  // silent for 10-20s" pattern.
  WiFi.setSleep(false);

  set_microros_wifi_transports((char*)WIFI_SSID, (char*)WIFI_PASSWORD, (char*)AGENT_IP, AGENT_PORT);

  delay(2000);

  allocator = rcl_get_default_allocator();
  RCCHECK(rclc_support_init(&support, 0, NULL, &allocator));
  RCCHECK(rclc_node_init_default(&node, "esp32_car_node", "", &support));

  RCCHECK(rclc_subscription_init_default(
      &twist_subscriber,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist),
      "/cmd_vel"));

  RCCHECK(rclc_executor_init(&executor, &support.context, 1, &allocator));
  RCCHECK(rclc_executor_add_subscription(&executor, &twist_subscriber, &twist_msg, &twist_callback, ON_NEW_DATA));

  Serial.println("micro-ROS init complete. Waiting for /cmd_vel...");
  last_cmd_time = millis();
}

void loop() {
  rclc_executor_spin_some(&executor, RCL_MS_TO_NS(100));

  if (millis() - last_cmd_time > CMD_TIMEOUT_MS) {
    if (!motors_timed_out) {
      Serial.println("No cmd_vel received recently - stopping motors (safety timeout).");
      motors_timed_out = true;
    }
    stopMotors();
  } else if (motors_timed_out) {
    Serial.println("cmd_vel resumed - motors active again.");
    motors_timed_out = false;
  }
}
