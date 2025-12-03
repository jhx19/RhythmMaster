import time
import board
import busio
import adafruit_adxl34x
import touchio # Used for capacitive touch detection
import digitalio # Used for D4/D5 simple digital inputs (if needed, otherwise remove)
import math

# --- ADXL345 Configuration Parameters ---
DOUBLE_TAP_INTERVAL_MS = 500.0
THRESHOLD = 8
MOVEMENT_COOLDOWN_SECONDS = 1.5
NUM_CALIBRATION_READS = 20

# --- 1. 触摸输入配置 (Capacitive Touch) ---
# 使用 D0, D1, D2, D3 进行电容式触摸检测
TOUCH_PINS = {
    "Pad 0 (D0)": board.D0,
    "Pad 1 (D1)": board.D1,
    "Pad 2 (D2)": board.D2, # 注意: D2现在用于触摸
    "Pad 3 (D3)": board.D3, # 注意: D3现在用于触摸
}
# 触摸对象和状态初始化变量
touch_objects = {}
last_touched_state = {}

# --- 2. ADXL345/I2C 初始化 ---
# 注意: board.D7 and board.D6 是 I2C 引脚。
i2c = busio.I2C(board.D7, board.D6)

try:
    # 初始化 ADXL345
    accelerometer = adafruit_adxl34x.ADXL345(i2c)
    accelerometer.enable_tap_detection()
    print("✅ ADXL345 initialized and tap detection enabled.")

    # 初始化所有 TouchIn 对象
    for name, pin in TOUCH_PINS.items():
        # 需要确保引脚不被 digitalio 或其他功能占用
        touch_objects[name] = touchio.TouchIn(pin)
        last_touched_state[name] = touch_objects[name].value
        
    print(f"✅ 成功初始化 {len(touch_objects)} 个触摸引脚 (D0-D3)。")

except Exception as e:
    print(f"❌ 初始化失败，请检查接线、引脚名称或库文件：{e}")
    while True:
        time.sleep(1)

# --- 3. 零点校准 (Baseline Calculation) ---
sum_x, sum_y, sum_z = 0.0, 0.0, 0.0
print("--- Starting ADXL345 Calibration ---")
for _ in range(NUM_CALIBRATION_READS):
    x, y, z = accelerometer.acceleration
    sum_x += x
    sum_y += y
    sum_z += z
    time.sleep(0.1)

av_x = sum_x / NUM_CALIBRATION_READS
av_y = sum_y / NUM_CALIBRATION_READS
av_z = sum_z / NUM_CALIBRATION_READS
print(f"Calibration Baselines: X={av_x:.3f}, Y={av_y:.3f}, Z={av_z:.3f}\n")

# --- 4. 状态/计时器变量初始化 ---
last_tap_time = 0.0 # Timestamp (in ms) of the last single tap event.
cooldown_until = 0.0 # Timestamp (in s) when the movement detection cooldown ends.


# --- 5. 辅助函数：触摸检测 ---
def check_touch_pad(name, touch_object, last_state):
    """检查单个触摸板的状态变化并打印。"""
    current_state = touch_object.value
    
    if current_state != last_state:
        if current_state:
            print(f"[触摸] 🟢 **{name}**: 开始触摸！")
        else:
            print(f"[触摸] 🔴 **{name}**: 停止触摸！")
        return current_state
    return last_state

# --- Main Loop ---
print("--- Starting Detection Loop ---")
while True:
    # --- A. Double Tap Detection ---
    if accelerometer.events["tap"]:
        current_time_ms = time.monotonic() * 1000.0
        time_diff = current_time_ms - last_tap_time

        if 100 < time_diff < DOUBLE_TAP_INTERVAL_MS:
            print(f"ADXL345: 💥 **DOUBLE TAP DETECTED**! Time Diff: {time_diff:.1f}ms")
            last_tap_time = 0.0
        else:
            last_tap_time = current_time_ms

    # --- B. X-axis Movement Detection (+X / -X with Cooldown) ---
    current_time_s = time.monotonic()

    # Skip movement direction checks if currently in a cooldown period.
    if current_time_s >= cooldown_until:
        x, y, z = accelerometer.acceleration
        x_cal = x - av_x # Calibrated X-axis acceleration

        # Check +X (Right) movement
        if x_cal > THRESHOLD:
            print(f"ADXL345: ➡️ **Moving +X (Right)**! Acceleration: {x_cal:.3f} m/s^2")
            cooldown_until = current_time_s + MOVEMENT_COOLDOWN_SECONDS
        # Check -X (Left) movement
        elif x_cal < -THRESHOLD:
            print(f"ADXL345: ⬅️ **Moving -X (Left)**! Acceleration: {x_cal:.3f} m/s^2")
            cooldown_until = current_time_s + MOVEMENT_COOLDOWN_SECONDS

    # --- C. Capacitive Touch (D0-D3) Detection ---
    for name, touch_obj in touch_objects.items():
        new_state = check_touch_pad(name, touch_obj, last_touched_state[name])
        if new_state != last_touched_state[name]:
            last_touched_state[name] = new_state
            
    # Short delay to control loop frequency
    time.sleep(0.02)
