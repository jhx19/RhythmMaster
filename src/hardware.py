import time
import board
import busio
import displayio
import terminalio
import neopixel
import pwmio
import touchio
import digitalio
import adafruit_adxl34x
import adafruit_displayio_ssd1306
from adafruit_display_text import label
from rotary_encoder import RotaryEncoder
from i2cdisplaybus import I2CDisplayBus
import settings

class HardwareManager:
    def __init__(self):
        print("Initializing Hardware...")
        
        # --- 1. I2C Setup (OLED & ADXL) ---
        # [cite_start]使用 settings.py 中的 D6/D7 [cite: 63]
        self.i2c = busio.I2C(settings.PIN_I2C_SCL, settings.PIN_I2C_SDA)

        # --- 2. Display Setup (OLED) ---
        displayio.release_displays()
        try:
            self.display_bus = I2CDisplayBus(self.i2c, device_address=0x3C)
            self.display = adafruit_displayio_ssd1306.SSD1306(
                self.display_bus, width=settings.SCREEN_WIDTH, height=settings.SCREEN_HEIGHT
            )
            self.main_group = displayio.Group()
            self.display.root_group = self.main_group
        except Exception as e:
            print(f"OLED Init Error: {e}")

        # --- 3. Sensor Setup (ADXL345) ---
        self.accel = adafruit_adxl34x.ADXL345(self.i2c)
        self.accel.enable_tap_detection(tap_count=1, threshold=20, duration=50, latency=20, window=255)
        
        # ADXL Logic Variables
        self.last_tap_time = 0.0
        self.cooldown_until = 0.0
        self.av_x = 0.0
        
        # 执行校准 (Calibration)
        self._calibrate_accelerometer()

        # --- 4. Inputs: Rotary Encoder & Button ---
        # Encoder Pins: D8, D9
        self.encoder = RotaryEncoder(settings.PIN_ENCODER_A, settings.PIN_ENCODER_B, debounce_ms=6, pulses_per_detent=3)
        self.last_encoder_pos = 0
        
        # Encoder Button: D10 (需设置为上拉输入)
        self.encoder_btn = digitalio.DigitalInOut(settings.PIN_ENCODER_BTN)
        self.encoder_btn.direction = digitalio.Direction.INPUT
        self.encoder_btn.pull = digitalio.Pull.UP

        # --- 5. Inputs: Capacitive Touch ---
        # [cite_start]Touch Pins: D0, D1, D2, D3 [cite: 63]
        self.touch_pads = {}
        # 映射 Move ID 到 触摸对象
        self.touch_map = {
            settings.MOVE_TOUCH_1: touchio.TouchIn(settings.PIN_TOUCH_1),
            settings.MOVE_TOUCH_2: touchio.TouchIn(settings.PIN_TOUCH_2),
            settings.MOVE_TOUCH_3: touchio.TouchIn(settings.PIN_TOUCH_3),
            settings.MOVE_TOUCH_4: touchio.TouchIn(settings.PIN_TOUCH_4)
        }
        # 设置阈值 (可选，根据硬件调整)
        for tp in self.touch_map.values():
            tp.threshold = tp.raw_value + 300

        # --- 6. Outputs: NeoPixel & Buzzer ---
        # [cite_start]NeoPixel: D4 [cite: 63]
        self.pixels = neopixel.NeoPixel(settings.PIN_NEOPIXEL, settings.NUM_PIXELS, brightness=0.3, auto_write=False)
        
        # [cite_start]Buzzer: D5 (PWM) - 初始化为静音 (Duty Cycle 65535, 低电平触发) [cite: 63]
        self.buzzer = pwmio.PWMOut(settings.PIN_BUZZER, duty_cycle=65535, frequency=440, variable_frequency=True)

    def _calibrate_accelerometer(self):
        """
        来自 input_test.py 的校准逻辑
        计算 X 轴的基准偏移量
        """
        print("--- Calibrating ADXL345 ---")
        sum_x = 0.0
        # [cite_start]读取 20 次取平均值 [cite: 63]
        for _ in range(20):
            x, y, z = self.accel.acceleration
            sum_x += x
            time.sleep(0.05)
        
        self.av_x = sum_x / 20.0
        print(f"Calibration Complete. Baseline X: {self.av_x:.3f}")

    def read_game_inputs(self):
        """
        游戏主循环中调用的输入检测函数。
        优先级：Double Tap > Touch > Tilt
        返回检测到的 Move ID (例如 settings.MOVE_TAP)，如果没有动作则返回 settings.MOVE_NONE
        """
        
        # 1. 检测 Double Tap (逻辑来自 input_test.py)
        if self.accel.events["tap"]:
            current_time_ms = time.monotonic() * 1000.0
            time_diff = current_time_ms - self.last_tap_time
            
            # [cite_start]判定双击的时间间隔 (100ms - 500ms) [cite: 63]
            if 100 < time_diff < 500.0:
                print("ACTION: Double Tap!")
                self.last_tap_time = 0.0 # 重置
                return settings.MOVE_TAP
            else:
                self.last_tap_time = current_time_ms

        # 2. 检测 Touch Pads (D0-D3)
        # 遍历所有触摸板，如果被触摸则返回对应的 MOVE ID
        for move_id, touch_obj in self.touch_map.items():
            if touch_obj.value:
                # 简单的防抖或去重可以在这里添加，或者在游戏逻辑层处理
                return move_id

        # 3. 检测 Tilt Left/Right (逻辑来自 input_test.py)
        # [cite_start]带有冷却时间 (1.5秒) [cite: 63]
        current_time_s = time.monotonic()
        if current_time_s >= self.cooldown_until:
            x, y, z = self.accel.acceleration
            x_cal = x - self.av_x # 使用校准后的值
            
            # 检测向右 (+X)
            if x_cal > settings.ADXL_THRESHOLD:
                print(f"ACTION: Right Tilt (X={x_cal:.2f})")
                self.cooldown_until = current_time_s + 1.5
                return settings.MOVE_RIGHT
            
            # 检测向左 (-X)
            elif x_cal < -settings.ADXL_THRESHOLD:
                print(f"ACTION: Left Tilt (X={x_cal:.2f})")
                self.cooldown_until = current_time_s + 1.5
                return settings.MOVE_LEFT

        return settings.MOVE_NONE

    def is_button_pressed(self):
        """
        检测 Encoder 按钮是否被按下 (低电平有效)
        返回: True (按下) / False (未按下)
        """
        return not self.encoder_btn.value

    def get_encoder_delta(self):
        """
        获取旋转编码器的变化量，并重置位置记录
        用于菜单导航
        """
        current_pos = self.encoder.position
        delta = current_pos - self.last_encoder_pos
        self.last_encoder_pos = current_pos
        return delta

    def display_text(self, text, scale=1, x_offset=5, y_offset=None):
        """
        在 OLED 上显示文本的辅助函数
        """
        if y_offset is None:
            y_offset = settings.SCREEN_HEIGHT // 2
            
        self.main_group = displayio.Group()
        text_area = label.Label(
            terminalio.FONT, 
            text=text, 
            scale=scale, 
            color=0xFFFFFF, 
            x=x_offset, 
            y=y_offset
        )
        self.main_group.append(text_area)
        self.display.root_group = self.main_group

    def play_tone(self, freq, duration):
        """
        播放蜂鸣器音调 
        注意：buzzer是低电平触发 (LOW=响, HIGH=静音)
        """
        PLAY_DUTY = 49152   # 约 75% 占空比 (实际上对应低电平触发的 25% 功率)
        SILENCE_DUTY = 65535 # 100% 占空比 = HIGH = 静音

        if freq > 0:
            self.buzzer.frequency = freq
            self.buzzer.duty_cycle = PLAY_DUTY
        else:
            self.buzzer.duty_cycle = SILENCE_DUTY
            
        time.sleep(duration)
        self.buzzer.duty_cycle = SILENCE_DUTY # 停止

    def set_leds(self, color):
        """设置所有 NeoPixel 的颜色"""
        self.pixels.fill(color)
        self.pixels.show()

    def set_pixel_segment(self, start, end, color):
        """设置 NeoPixel 的某一段 (用于蛇形灯效等)"""
        for i in range(start, end):
             if 0 <= i < settings.NUM_PIXELS:
                self.pixels[i] = color
        self.pixels.show()