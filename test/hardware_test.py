import time
import board
import settings
import songs
from hardware import HardwareManager

# --- 0. 视觉颜色定义 (根据你的要求优化) ---
COLOR_NICE_GREEN = (30, 255, 30)    # 更饱和的绿色 (Touch)
COLOR_NICE_RED   = (231, 76, 60)    # 柔和红 (Double Tap)
COLOR_BLACK      = (0, 0, 0)

# 蓝色渐变阶梯 (从深到浅，引入亮度模拟)
# 使用整数运算来调整亮度
GRADIENT_BLUE = [
    # Track 0: 最深蓝 (亮度降低)
    (0, 0, 80),     
    # Track 1: 中深蓝 (亮度略降)
    (0, 72, 162),    
    # Track 2: 中浅蓝 (全亮度)
    (80, 160, 220),  
    # Track 3: 浅蓝/白蓝 (全亮度)
    (180, 240, 255)  
]
def get_physical_index(track_idx, vis_pos):
    """
    蛇形走线映射逻辑：
    Track 0 (0-6): 正向
    Track 1 (7-13): 反向 (13-pos)
    Track 2 (14-20): 正向
    Track 3 (21-27): 反向 (27-pos)
    """
    if track_idx == 0: return 0 + vis_pos
    if track_idx == 1: return 13 - vis_pos
    if track_idx == 2: return 14 + vis_pos
    if track_idx == 3: return 27 - vis_pos
    return -1

def draw_visuals_test(hw, timeline, current_time, look_ahead=1.4):
    """
    模拟游戏引擎的绘制逻辑，测试灯带映射和颜色。
    """
    hw.pixels.fill(COLOR_BLACK)
    
    # 只需要绘制未来 0.7秒内的音符
    for note in timeline:
        time_until_hit = note['target_time'] - current_time
        
        if 0 <= time_until_hit <= look_ahead:
            # 计算位置 (0 = 判定线, 6 = 顶部)
            ratio = 1.0 - (time_until_hit / look_ahead)
            local_pos = int(ratio * 7)
            local_pos = max(0, min(6, local_pos))
            
            move_id = note['move']
            
            # --- 绘制逻辑 ---
            
            # 1. 特殊动作：全轨道显示
            if move_id in [settings.MOVE_TAP, settings.MOVE_LEFT, settings.MOVE_RIGHT]:
                for t_idx in range(4):
                    phys_idx = get_physical_index(t_idx, local_pos)
                    
                    color = COLOR_NICE_RED # Default Tap
                    
                    if move_id == settings.MOVE_LEFT:
                        color = GRADIENT_BLUE[t_idx] # 深 -> 浅
                    elif move_id == settings.MOVE_RIGHT:
                        color = GRADIENT_BLUE[3 - t_idx] # 浅 -> 深
                        
                    if 0 <= phys_idx < settings.NUM_PIXELS:
                        hw.pixels[phys_idx] = color
            
            # 2. 普通 Touch：单轨道显示 (绿色)
            elif move_id in [settings.MOVE_TOUCH_1, settings.MOVE_TOUCH_2, settings.MOVE_TOUCH_3, settings.MOVE_TOUCH_4]:
                target_track = 0
                if move_id == settings.MOVE_TOUCH_2: target_track = 1
                if move_id == settings.MOVE_TOUCH_3: target_track = 2
                if move_id == settings.MOVE_TOUCH_4: target_track = 3
                
                phys_idx = get_physical_index(target_track, local_pos)
                if 0 <= phys_idx < settings.NUM_PIXELS:
                    hw.pixels[phys_idx] = COLOR_NICE_GREEN

    hw.pixels.show()

def run_hardware_test():
    print("=== GIX Rhythm Master Hardware Test ===")
    
    # 1. 初始化硬件
    hw = HardwareManager()
    
    # 2. 测试 OLED 显示
    print("\n[Test 1] Display Test...")
    hw.display_layers([
        {'text': "HARDWARE", 'scale': 1, 'y': 10},
        {'text': "TEST MODE", 'scale': 2, 'y': 35},
        {'text': "Press Btn", 'scale': 1, 'y': 60}
    ])
    
    # 等待按下编码器按钮继续
    while True:
        if hw.is_button_pressed():
            break
        time.sleep(0.1)
    
    # 3. 传感器输入循环测试
    print("\n[Test 2] Input Sensor Check (10 seconds)")
    print("Try: Touching pads, Tapping device, Tilting Left/Right...")
    
    while True:
        if hw.is_button_pressed():
            break
        user_input = hw.read_game_inputs()
        encoder_delta = hw.get_encoder_delta()
        
        input_text = "NONE"
        if user_input == settings.MOVE_TOUCH_1: input_text = "TOUCH 1"
        elif user_input == settings.MOVE_TOUCH_2: input_text = "TOUCH 2"
        elif user_input == settings.MOVE_TOUCH_3: input_text = "TOUCH 3"
        elif user_input == settings.MOVE_TOUCH_4: input_text = "TOUCH 4"
        elif user_input == settings.MOVE_TAP:     input_text = "DOUBLE TAP!"
        elif user_input == settings.MOVE_LEFT:    input_text = "TILT LEFT"
        elif user_input == settings.MOVE_RIGHT:   input_text = "TILT RIGHT"
        
        # 只有当有输入时才刷新屏幕，避免闪烁太快
        if user_input != settings.MOVE_NONE or encoder_delta != 0:
            print(f"Detected: {input_text} | Enc: {encoder_delta}")
            hw.display_layers([
                {'text': "Input Test", 'scale': 1, 'y': 5},
                {'text': input_text, 'scale': 2, 'y': 32},
                {'text': f"Enc: {encoder_delta}", 'scale': 1, 'y': 58}
            ])
            
            # 简单的灯光反馈
            hw.pixels.fill((0,0,0))
            if user_input != settings.MOVE_NONE:
                hw.pixels.fill((20, 20, 20)) # 微亮白光表示检测到
            hw.pixels.show()
            
        time.sleep(0.05)

    # 4. 音频与灯带同步测试 (播放 Twinkle Star)
    print("\n[Test 3] Song Sync Test (Twinkle Star)")
    hw.display_layers([
        {'text': "Sync Test", 'scale': 1, 'y': 20},
        {'text': "Playing...", 'scale': 2, 'y': 40}
    ])
    
    # 预处理乐谱 (转换为绝对时间)
    raw_song = songs.SONG_LIBRARY[0] # Twinkle Star
    timeline = []
    curr_t = 0.0
    bpm = raw_song["bpm_scale"]
    # 解析 steps
    for note_name, duration, move_input in raw_song["steps"]:
        # 处理 move_input 可能是列表的情况，这里为了测试只取第一个
        target_move = move_input
        if isinstance(move_input, list):
            target_move = move_input[0] if len(move_input) > 0 else settings.MOVE_NONE
        duration = bpm * duration
        freq = songs.get_frequency(note_name)
        timeline.append({
            'target_time': curr_t,
            'freq': freq,
            'duration': duration,
            'move': target_move,
            'played': False
        })
        curr_t += duration

    total_duration = curr_t
    start_time = time.monotonic()
    
    # 模拟游戏循环
    while True:
        now = time.monotonic()
        song_time = now - start_time
        
        if song_time > total_duration + 1.0:
            break
            
        # A. 视觉更新 (Look ahead)
        draw_visuals_test(hw, timeline, song_time)
        
        # B. 音频更新
        # 简单的播放逻辑：如果时间到了且没播过，就播
        for note in timeline:
            if not note['played'] and song_time >= note['target_time']:
                note['played'] = True
                print(f"Playing {note['freq']}Hz at {song_time:.2f}s")
                
                # 注意：hw.play_tone 是阻塞的(sleep)。
                # 为了保持灯光流畅，这里我们稍微改一下逻辑：
                # 实际游戏中应该使用非阻塞PWM，但为了测试硬件，
                # 我们允许短暂的阻塞，或者你可以缩短 duration 测试点亮情况
                if note['freq'] > 0:
                    # 播放 0.1秒 听个响即可，避免阻塞太久导致灯光卡顿
                    hw.play_tone(note['freq'], 0.15) 
                break # 一帧只触发一个音

    # 结束
    hw.set_leds((0,0,0))
    hw.display_layers([
        {'text': "TEST COMPLETE", 'scale': 1, 'y': 32}
    ])
    print("Test Complete.")

if __name__ == "__main__":
    run_hardware_test()
