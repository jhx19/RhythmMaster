# settings.py (在原有基础上增加)
import board

# ... (保留你原有的 Pin Definitions 和 Game Constants) ...
PIN_TOUCH_1 = board.D0
PIN_TOUCH_2 = board.D1
PIN_TOUCH_3 = board.D2
PIN_TOUCH_4 = board.D3
PIN_NEOPIXEL = board.D4
PIN_I2C_SCL = board.D5  # 注意：这里和你的硬件描述一致
PIN_I2C_SDA = board.D6
PIN_BUZZER = board.D7
PIN_ENCODER_A = board.D8
PIN_ENCODER_B = board.D9
PIN_ENCODER_BTN = board.D10

DIFFICULTY_EASY = 0
DIFFICULTY_MED = 1
DIFFICULTY_HARD = 2
DIFFICULTY_NAMES = ["EASY", "NORMAL", "HARD"] # 用于显示

BPM = [2, 1.2, 0.7] 
DURATION = [0.2, 0.15, 0.1] 
SCORE_FACTOR = [1, 1.5, 2] 

# --- New Constants ---
MAX_GAME_LEVELS = 10  # 总共10关
NUM_HIGHSCORES = 6

# ... (保留 Hardware Constants 和 Move Definitions) ...
NUM_PIXELS = 28  
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
ADXL_THRESHOLD = 6 

MOVE_NONE = 0 
MOVE_TOUCH_1 = 1
MOVE_TOUCH_2 = 2
MOVE_TOUCH_3 = 3
MOVE_TOUCH_4 = 4
MOVE_RIGHT = 5
MOVE_LEFT = 6
MOVE_TAP = 7

MOVES_LIST = ["TOUCH1","TOUCH2","TOUCH3","TOUCH4","LEFT","RIGHT","DOUBLETAP"]

COLOR_NICE_GREEN = (30, 255, 30)
COLOR_NICE_RED   = (231, 76, 60)
COLOR_BLACK      = (0, 0, 0)
GRADIENT_BLUE = [
    (0, 0, 50),     
    (0, 60, 140),    
    (80, 160, 220),  
    (180, 255, 255)  
]

QN = 0.4
HN = 0.8

