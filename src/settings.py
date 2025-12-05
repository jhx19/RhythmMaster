# settings.py
import board

# --- Pin Definitions ---
PIN_TOUCH_1 = board.D0
PIN_TOUCH_2 = board.D1
PIN_TOUCH_3 = board.D2
PIN_TOUCH_4 = board.D3
PIN_NEOPIXEL = board.D4
PIN_BUZZER = board.D5
PIN_I2C_SDA = board.D6
PIN_I2C_SCL = board.D7
PIN_ENCODER_A = board.D8
PIN_ENCODER_B = board.D9
PIN_ENCODER_BUTTON = board.D10
# --- Game Constants ---
DIFFICULTY_EASY = 0
DIFFICULTY_MED = 1
DIFFICULTY_HARD = 2

# Time limits (in seconds) based on difficulty
TIME_LIMITS = {
    DIFFICULTY_EASY: 5.0,
    DIFFICULTY_MED: 3.0,
    DIFFICULTY_HARD: 1.5
}

# --- Hardware Constants ---
NUM_PIXELS = 28  
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
ADXL_THRESHOLD = 8 # Accelerometer movement threshold

# --- Move Definitions ---
MOVE_NONE = 0 
MOVE_TOUCH_1 = 1
MOVE_TOUCH_2 = 2
MOVE_TOUCH_3 = 3
MOVE_TOUCH_4 = 4
MOVE_RIGHT = 5
MOVE_LEFT = 6
MOVE_TAP = 7

MOVES_LIST = ["TOUCH1","TOUCH2","TOUCH3","TOUCH4","LEFT","RIGHT","DOUBLETAP"]