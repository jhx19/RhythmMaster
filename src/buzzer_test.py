import board
import time
import pwmio

# --- 定义占空比常量 (低电平触发) ---
# 播放时占空比 (1/4 音量，柔和)
PLAY_DUTY = 49152 

# 静音时占空比 (100% HIGH，低电平触发)
SILENCE_DUTY = 65535 

# --- 硬件配置 ---
# 连接到 D5，初始化为静音 (HIGH)
buzzer = pwmio.PWMOut(board.D5, duty_cycle=SILENCE_DUTY, frequency=440, variable_frequency=True)


# --- 音符频率表 (Hz) ---
NOTES = {
    'C4': 262, 'D4': 294, 'E4': 330, 'F4': 349, 'G4': 392, 
    'A4': 440, 'REST': 0
}

# --- 核心功能: 播放单音 ---
def play_tone(freq, duration_ms):
    """
    驱动低电平触发蜂鸣器播放单音
    """
    
    if freq > 0:
        # --- 发声逻辑 ---
        buzzer.frequency = freq
        buzzer.duty_cycle = PLAY_DUTY # 50% 占空比
        
    else:
        # --- 静音逻辑 ---
        buzzer.duty_cycle = SILENCE_DUTY # 100% 占空比 (HIGH)
        
    # 保持发声或静音指定的时间
    time.sleep(duration_ms / 1000.0)
    
    # --- 停止：回到静音状态，保证音符间隔 ---
    buzzer.duty_cycle = SILENCE_DUTY


# --- 《小星星》乐谱 (C C G G A A G - | F F E E D D C - ) ---
# 格式: (音符名称, 持续时间ms)
# 默认四分音符 (QN) = 500ms, 二分音符 (HN) = 1000ms
QN = 300
HN = 600
REST_DUR = 50 # 音符间隔

twinkle_twinkle = [
    ('C4', QN), ('C4', QN), ('REST', REST_DUR),
    ('G4', QN), ('G4', QN), ('REST', REST_DUR),
    ('A4', QN), ('A4', QN), ('REST', REST_DUR),
    ('G4', HN), ('REST', REST_DUR),
    
    ('F4', QN), ('F4', QN), ('REST', REST_DUR),
    ('E4', QN), ('E4', QN), ('REST', REST_DUR),
    ('D4', QN), ('D4', QN), ('REST', REST_DUR),
    ('C4', HN), ('REST', REST_DUR),
    
    # 变奏部分 (G G F F E E D -)
    ('G4', QN), ('G4', QN), ('REST', REST_DUR),
    ('F4', QN), ('F4', QN), ('REST', REST_DUR),
    ('E4', QN), ('E4', QN), ('REST', REST_DUR),
    ('D4', HN), ('REST', REST_DUR),
    
    ('G4', QN), ('G4', QN), ('REST', REST_DUR),
    ('F4', QN), ('F4', QN), ('REST', REST_DUR),
    ('E4', QN), ('E4', QN), ('REST', REST_DUR),
    ('D4', HN), ('REST', REST_DUR),
    
    # 循环第一段
    ('C4', QN), ('C4', QN), ('REST', REST_DUR),
    ('G4', QN), ('G4', QN), ('REST', REST_DUR),
    ('A4', QN), ('A4', QN), ('REST', REST_DUR),
    ('G4', HN), ('REST', REST_DUR),
    
    ('F4', QN), ('F4', QN), ('REST', REST_DUR),
    ('E4', QN), ('E4', QN), ('REST', REST_DUR),
    ('D4', QN), ('D4', QN), ('REST', REST_DUR),
    ('C4', HN)
]

print("开始播放《小星星》...")

while True:
    for note_name, duration in twinkle_twinkle:
        freq = NOTES.get(note_name, 0)
        
        # 播放音符
        play_tone(freq, duration)
        
    print("歌曲播放完毕，休息3秒...")
    time.sleep(3)
