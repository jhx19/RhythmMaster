import time
import board
import busio
import pwmio
import neopixel
import adafruit_adxl34x
import touchio
import math

# ================= 核心配置区域 (请根据实际硬件调整) =================

# --- 引脚配置 ---
PIN_TOUCH = [board.D0, board.D1, board.D2, board.D3]
PIN_NEOPIXEL = board.D4
PIN_BUZZER = board.D5
PIN_I2C_SCL = board.D7
PIN_I2C_SDA = board.D6

# --- NeoPixel 映射和颜色 ---
NUM_PIXELS = 28
LEDS_PER_SEGMENT = 7
COLOR_TOUCH = (0, 255, 0) # 绿色 (所有触摸键)
COLOR_JOY_LEFT = (0, 0, 255) # 蓝色 (摇杆左)
COLOR_JOY_RIGHT = (255, 0, 0) # 红色 (摇杆右)
COLOR_HIT = (255, 255, 255) # 白色 (命中闪烁)

# --- 游戏计时和判定 ---
NOTE_FALL_TIME = 3500 # 3.5秒 (7个LED * 0.5秒/LED)
TIME_BETWEEN_PIXELS = NOTE_FALL_TIME / (LEDS_PER_SEGMENT - 1) # 583.33ms/LED
WINDOW_PERFECT = 80   # 完美判定窗口: +/- 80ms
WINDOW_GOOD = 200     # 良好判定窗口: +/- 200ms

# --- ADXL345 设置 ---
JOYSTICK_THRESHOLD = 7.0
TAP_THRESHOLD = 20
DUTY_OFF = 65535 # 蜂鸣器静音
DUTY_ON = 49152  # 蜂鸣器发声

# --- 蛇形灯带物理映射 (核心 helper) ---
SEGMENT_MAP = {
    0: {'start': 0, 'end': 6, 'dir': 1},   # Track 0: 0 -> 6 (Jude=0)
    1: {'start': 13, 'end': 7, 'dir': -1}, # Track 1: 13 -> 7 (Jude=7)
    2: {'start': 14, 'end': 20, 'dir': 1}, # Track 2: 14 -> 20 (Jude=14)
    3: {'start': 27, 'end': 21, 'dir': -1},# Track 3: 27 -> 21 (Jude=21)
}
# 判定线（Jude Line）的物理索引
JUDE_LINE_INDEXES = {0: 6, 1: 7, 2: 20, 3: 21}

# --- 音符频率表 ---
NOTES = {'C4': 262, 'D4': 294, 'E4': 330, 'F4': 349, 'G4': 392, 'A4': 440, 'REST': 0}

# ================= 硬件初始化类 =================

class Hardware:
    # (省略了 __init__ 和 check_inputs 函数，沿用上一个回复中的完整逻辑，确保代码简洁)
    # 实际项目中请使用上一个回复中的完整 Hardware 类

    def __init__(self):
        print("Initializing Hardware...")
        self.i2c = busio.I2C(PIN_I2C_SCL, PIN_I2C_SDA)
        self.accel = adafruit_adxl34x.ADXL345(self.i2c)
        self.accel.enable_tap_detection(tap_count=2, threshold=TAP_THRESHOLD)
        x_sum = sum(self.accel.acceleration[0] for _ in range(10))
        self.joy_rest_x = x_sum / 10
        self.pixels = neopixel.NeoPixel(PIN_NEOPIXEL, NUM_PIXELS, brightness=0.3, auto_write=False)
        self.buzzer = pwmio.PWMOut(PIN_BUZZER, duty_cycle=DUTY_OFF, frequency=440, variable_frequency=True)
        self.touch_pads = [touchio.TouchIn(p) for p in PIN_TOUCH]
        print(f"ADXL Ready. Joy Rest X: {self.joy_rest_x:.2f}")

    def set_tone(self, freq):
        """非阻塞设置蜂鸣器"""
        if freq > 0:
            self.buzzer.frequency = freq
            self.buzzer.duty_cycle = DUTY_ON
        else:
            self.buzzer.duty_cycle = DUTY_OFF

    def check_inputs(self):
        """返回当前所有输入状态的字典 (0-3:Keys, 4:Left, 5:Right, 'tap':bool)"""
        inputs = {}
        for i, pad in enumerate(self.touch_pads):
            inputs[i] = pad.value
        
        x = self.accel.acceleration[0]
        diff = x - self.joy_rest_x
        inputs[4] = diff < -JOYSTICK_THRESHOLD # Left
        inputs[5] = diff > JOYSTICK_THRESHOLD  # Right
        inputs['tap'] = self.accel.events['tap']
        return inputs
    
    def clear_pixels(self):
        self.pixels.fill((0,0,0))
        self.pixels.show()

# ================= 游戏逻辑类 =================

class RhythmGameTest:
    def __init__(self, hw, song_data):
        self.hw = hw
        self.song = song_data
        self.active_notes = [] # [target_time, track, freq, duration, is_hit, hit_type]
        self.score = 0
        self.combo = 0
        self.feedback_text = ""
        self.hit_effect_time = 0
        self.last_move_joy_time = 0 # 避免摇杆信号被连续触发

    def start(self):
        print("\n=== 游戏开始: 节奏大师蛇形测试 ===")
        self.start_time = time.monotonic() * 1000
        self.note_idx = 0
        
    def _map_logic_to_physical(self, track_id, logical_pos):
        """将逻辑位置 (0=Jude, 6=Spawn) 映射到物理灯珠索引"""
        if not 0 <= track_id <= 3: return [] # 摇杆操作不走这个逻辑
        
        segment = SEGMENT_MAP[track_id]
        
        # 0到6的逻辑位置映射到 0到6的 segment 索引
        segment_idx = int(round(logical_pos)) 
        segment_idx = max(0, min(LEDS_PER_SEGMENT - 1, segment_idx))
        
        if segment['dir'] == 1: # 正向 (0->6, 14->20)
            physical_idx = segment['start'] + segment_idx
        else: # 反向 (13->7, 27->21)
            physical_idx = segment['start'] - segment_idx
            
        return [physical_idx]

    def _render_joystick(self, joy_track_id, joy_color):
        """摇杆特殊渲染：所有轨道一起亮起"""
        # 遍历所有灯珠，设置颜色
        self.hw.pixels.fill(joy_color) 
        
    def run_loop(self):
        current_time = time.monotonic() * 1000 - self.start_time
        
        # 1. 生成音符 (Spawner)
        while self.note_idx < len(self.song):
            note_time, track, freq, dur, player_op = self.song[self.note_idx]
            spawn_time = note_time - NOTE_FALL_TIME
            
            if current_time >= spawn_time:
                # [target_time, track, freq, duration, is_hit, hit_type]
                self.active_notes.append([note_time, track, freq, dur, False, ''])
                self.note_idx += 1
            else:
                break
                
        # 2. 音频引擎 (Audio Engine)
        target_audio_freq = 0
        for note in self.active_notes:
            start_t = note[0]
            end_t = note[0] + note[3]
            if start_t <= current_time < end_t and note[5] != 'MISS':
                target_audio_freq = note[2]
                break
        
        self.hw.set_tone(target_audio_freq)

        # 3. 渲染灯光 (Visuals)
        self.hw.pixels.fill((0,0,0))
        
        # 检查是否有摇杆操作的音符正在下落
        joy_note_color = None
        for note in self.active_notes:
            if not note[4] and (note[1] == 4 or note[1] == 5):
                joy_note_color = COLOR_JOY_LEFT if note[1] == 4 else COLOR_JOY_RIGHT
                break
        
        # 特殊处理：如果摇杆音符存在，则执行特殊渲染
        if joy_note_color:
            self._render_joystick(note[1], joy_note_color)
        else:
            # 正常渲染触摸音符
            for note in self.active_notes:
                if note[4] or note[1] > 3: continue # 摇杆音符由特殊渲染处理

                time_left = note[0] - current_time
                if time_left < 0 or time_left > NOTE_FALL_TIME: continue
                
                # 计算逻辑位置 (0=Jude, 6=Spawn)
                logical_pos = (time_left / NOTE_FALL_TIME) * (LEDS_PER_SEGMENT - 1)
                
                # 映射到物理索引并点亮
                for idx in self._map_logic_to_physical(note[1], logical_pos):
                    self.hw.pixels[idx] = COLOR_TOUCH
                    
        self.hw.pixels.show()

        # 4. 输入判定 (Input & Scoring)
        inputs = self.hw.check_inputs()
        
        # 检查暂停
        if inputs.get('tap'):
            print(">>> 暂停 (Double Tap Detected) <<<")
            self.hw.set_tone(0)
            time.sleep(1) 
            self.start_time += 1000 # 补偿暂停的时间
            
        # 遍历所有被触发的输入
        for track_id, triggered in inputs.items():
            if track_id == 'tap': continue
            
            # 摇杆操作的冷却时间 (防止一次动作重复触发多次)
            if track_id >= 4 and time.monotonic() * 1000 < self.last_move_joy_time + 500:
                triggered = False

            if triggered:
                self.last_move_joy_time = time.monotonic() * 1000 # 记录操作时间

                best_note = None
                min_diff = 9999
                
                for note in self.active_notes:
                    if note[1] == track_id and not note[4]:
                        diff = abs(current_time - note[0])
                        if diff < min_diff:
                            min_diff = diff
                            best_note = note
                
                # 判定逻辑
                if best_note and min_diff <= WINDOW_GOOD:
                    hit_type = "MISS"
                    if min_diff <= WINDOW_PERFECT:
                        hit_type = "PERFECT"
                        self.combo += 1
                        self.score += 100
                    elif min_diff <= WINDOW_GOOD:
                        hit_type = "GOOD"
                        self.combo += 1
                        self.score += 50
                    
                    print(f"HIT! Track {track_id} | {hit_type} | Combo: {self.combo}{'!'*min(3, self.combo)}")
                    
                    best_note[4] = True 
                    best_note[5] = hit_type
                    self.hw.set_tone(best_note[2]) 
                else:
                    # 如果按了没中，combo中断
                    self.combo = 0
                    
        # 5. 清理过时音符 (Miss Check)
        for i in range(len(self.active_notes) - 1, -1, -1):
            note = self.active_notes[i]
            # 漏键判定 (Miss) - 超过判定窗口后未击中
            if current_time > note[0] + WINDOW_GOOD and not note[4]:
                print(f"MISS! Track {note[1]}")
                self.combo = 0
                note[4] = True 
                note[5] = 'MISS'
            
            # 移除已处理音符
            if current_time > note[0] + note[3] + 500:
                self.active_notes.pop(i)
                
        # 6. 打印得分
        print(f"Time: {current_time/1000:.2f}s | Score: {self.score} | Combo: {self.combo}", end='\r')

        return self.note_idx < len(self.song) or len(self.active_notes) > 0


# ================= 歌曲数据 (Chart) - 简化版 =================
# 格式: (触发时间ms, 轨道ID, 频率Hz, 持续时间ms, 玩家操作)
# 轨道: 0-3=触摸, 4=左倾, 5=右倾
QN = 500
HN = 1000

song_twinkle_simplified = [
    # C C G G A A G (只有G, A, 摇杆 需要操作)
    (1000, -1, NOTES['C4'], QN, False), # C4 (背景音, 无操作)
    (1500, -1, NOTES['C4'], QN, False),
    (2000, 1, NOTES['G4'], QN, True),  # G4 -> Track 1 (操作)
    (2500, 1, NOTES['G4'], QN, True),  # G4 -> Track 1 (操作)
    (3000, 4, NOTES['A4'], QN, True),  # A4 -> Left Joystick! (操作)
    (3500, 5, NOTES['A4'], QN, True),  # A4 -> Right Joystick! (操作)
    (4000, -1, NOTES['G4'], HN, False),# G4 (长音, 无操作)
    
    # F F E E D D C
    (5500, 3, NOTES['F4'], QN, True),  # F4 -> Track 3 (操作)
    (6000, -1, NOTES['F4'], QN, False),
    (6500, 2, NOTES['E4'], QN, True),  # E4 -> Track 2 (操作)
    (7000, -1, NOTES['E4'], QN, False),
    (7500, 0, NOTES['D4'], QN, True),  # D4 -> Track 0 (操作)
    (8000, 0, NOTES['D4'], QN, True),  # D4 -> Track 0 (操作)
    (8500, -1, NOTES['C4'], HN, False),# C4 (长音, 无操作)
]

# 最终谱面：只包含需要玩家操作的音符
# filter(lambda x: x[4], song_twinkle_simplified) # 实际在 Game Engine 中根据 track_id != -1 来区分

LEVEL_1_CHART = [n for n in song_twinkle_simplified if n[1] != -1]


# ================= 主程序测试入口 =================

hw = Hardware()
game = RhythmGameTest(hw, LEVEL_1_CHART)
background_music = [n for n in song_twinkle_simplified if n[1] == -1]
bg_music_idx = 0
bg_music_start_time = 0

if hw.accel and len(hw.touch_pads) == 4:
    game.start()
    running = True
    bg_music_start_time = time.monotonic() * 1000
    
    while running:
        # 背景音乐播放 (非玩家操作音符)
        current_bg_time = time.monotonic() * 1000 - bg_music_start_time
        while bg_music_idx < len(background_music):
            note_time, track, freq, dur, op = background_music[bg_music_idx]
            if current_bg_time >= note_time:
                hw.set_tone(freq)
                time.sleep(dur / 1000.0) # 此处使用 sleep 模拟背景音乐播放
                hw.set_tone(0) # 停止
                bg_music_idx += 1
            else:
                break
        
        # 游戏主逻辑
        running = game.run_loop()
        
        # 确保循环频率
        time.sleep(0.01) 
        
    print(f"\nGame Over! Final Score: {game.score} | Max Combo: {game.combo}")
    hw.set_tone(0)
    hw.clear_pixels()
else:
    print("硬件初始化不完整，无法开始游戏。")