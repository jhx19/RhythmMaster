import time
import board
import busio
import displayio
import terminalio
import neopixel
import pwmio
import touchio
import digitalio
import rotaryio  
import adafruit_adxl34x
import adafruit_displayio_ssd1306
from adafruit_display_text import label
from i2cdisplaybus import I2CDisplayBus
import settings

class HardwareManager:
    def __init__(self):
        print("Initializing Hardware (rotaryio version)...")
        displayio.release_displays()
        # --- 1. I2C Setup (OLED & ADXL) ---
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
        self.encoder = rotaryio.IncrementalEncoder(settings.PIN_ENCODER_A, settings.PIN_ENCODER_B)
        self.last_encoder_pos = 0
        
        # Encoder Button: D10 
        self.encoder_btn = digitalio.DigitalInOut(settings.PIN_ENCODER_BTN)
        self.encoder_btn.direction = digitalio.Direction.INPUT
        self.encoder_btn.pull = digitalio.Pull.UP
        self.last_btn_state = True  

        # --- 5. Inputs: Capacitive Touch ---
        # Touch Pins: D0, D1, D2, D3 
        self.touch_pads = {}
        self.touch_map = {
            settings.MOVE_TOUCH_1: touchio.TouchIn(settings.PIN_TOUCH_1),
            settings.MOVE_TOUCH_2: touchio.TouchIn(settings.PIN_TOUCH_2),
            settings.MOVE_TOUCH_3: touchio.TouchIn(settings.PIN_TOUCH_3),
            settings.MOVE_TOUCH_4: touchio.TouchIn(settings.PIN_TOUCH_4)
        }
        # (Edge Detection)
        self.last_touch_state = {move_id: False for move_id in self.touch_map.keys()}

        for tp in self.touch_map.values():
           new_threshold = tp.raw_value + 1500
           tp.threshold = min(new_threshold, 65535)

        # --- 6. Outputs: NeoPixel & Buzzer ---
        # NeoPixel: D4 
        self.pixels = neopixel.NeoPixel(settings.PIN_NEOPIXEL, settings.NUM_PIXELS, brightness=0.3, auto_write=False)
        
        # Buzzer: D5 (PWM) - 
        self.buzzer = pwmio.PWMOut(settings.PIN_BUZZER, duty_cycle=65535, frequency=440, variable_frequency=True)

    def _calibrate_accelerometer(self):
        print("--- Calibrating ADXL345 ---")
        sum_x = 0.0
        for _ in range(20):
            x, y, z = self.accel.acceleration
            sum_x += x
            time.sleep(0.05)
        
        self.av_x = sum_x / 20.0
        print(f"Calibration Complete. Baseline X: {self.av_x:.3f}")

    def read_game_inputs(self):
        # 1. Touch Pads 
        detected_touch = settings.MOVE_NONE
        for move_id, touch_obj in self.touch_map.items():
            current_state = touch_obj.value
            if current_state and not self.last_touch_state[move_id]:
                detected_touch = move_id
                break 
            self.last_touch_state[move_id] = current_state

        if detected_touch != settings.MOVE_NONE:
            return detected_touch

        # 2. Tilt Left/Right
        current_time_s = time.monotonic()
        if current_time_s >= self.cooldown_until:
            x, y, z = self.accel.acceleration
            x_cal = x - self.av_x 
            
            # tilt (+X)
            if x_cal > settings.ADXL_THRESHOLD:
                print(f"ACTION: Right Tilt (X={x_cal:.2f})")
                self.cooldown_until = current_time_s + 1.5
                return settings.MOVE_LEFT
            
            # tilt (-X)
            elif x_cal < -settings.ADXL_THRESHOLD:
                print(f"ACTION: Left Tilt (X={x_cal:.2f})")
                self.cooldown_until = current_time_s + 1.5
                return settings.MOVE_RIGHT
            
        # 3. Double Tap
        if self.accel.events["tap"]:
            current_time_ms = time.monotonic() * 1000.0
            time_diff = current_time_ms - self.last_tap_time

            if 150 < time_diff < 300.0:
                print("ACTION: Double Tap!")
                self.last_tap_time = 0.0 
                return settings.MOVE_TAP
            else:
                self.last_tap_time = current_time_ms

        return settings.MOVE_NONE

    def is_button_pressed(self):
        current_state = self.encoder_btn.value  

        is_pressed_now = (not current_state) and self.last_btn_state
        self.last_btn_state = current_state
        return is_pressed_now

    def get_encoder_delta(self):

        current_pos = self.encoder.position
        delta = current_pos - self.last_encoder_pos
        
        STEP = 1
        
        if abs(delta) >= STEP:
            steps = delta // STEP
            
            self.last_encoder_pos += steps * STEP
            return steps
            
        return 0

    def display_layers(self, layers):
        self.main_group.hidden = True 
        while self.main_group:
            self.main_group.pop()
        
        for layer in layers:
            text = layer['text']
            scale = layer.get('scale', 1)
            
            text_width = len(text) * 6 * scale 
            default_x = (settings.SCREEN_WIDTH - text_width) // 2
            
            x = layer.get('x', default_x)
            y = layer.get('y', settings.SCREEN_HEIGHT // 2)
            
            text_label = label.Label(
                terminalio.FONT, 
                text=text, 
                scale=scale, 
                color=0xFFFFFF, 
                x=x, 
                y=y
            )
            self.main_group.append(text_label)

        self.main_group.hidden = False

    def display_text(self, text, scale=1, x_offset=5, y_offset=None):
        if y_offset is None:
            y_offset = settings.SCREEN_HEIGHT // 2
            
        self.display_layers([
            {'text': text, 'scale': scale, 'x': x_offset, 'y': y_offset}
        ])

    def play_tone(self, freq, duration):
        PLAY_DUTY = 49152   
        SILENCE_DUTY = 65535 

        if freq > 0:
            self.buzzer.frequency = freq
            self.buzzer.duty_cycle = PLAY_DUTY
        else:
            self.buzzer.duty_cycle = SILENCE_DUTY
            
        time.sleep(duration)
        self.buzzer.duty_cycle = SILENCE_DUTY 

    def set_leds(self, color):
        self.pixels.fill(color)
        self.pixels.show()

    def set_pixel_segment(self, start, end, color):
        for i in range(start, end):
             if 0 <= i < settings.NUM_PIXELS:
                self.pixels[i] = color
        self.pixels.show()
