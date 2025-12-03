import time
import settings

class RhythmGame:
    def __init__(self, hardware, song_data):
        self.hw = hardware
        self.song_data = song_data
        
        # --- 游戏参数 ---
        self.score = 0
        self.is_game_over = False
        self.is_won = False
        
        # 灯光流速参数 (x): 
        # 值越小，音符掉落越快。0.1 表示每颗灯珠走 0.1秒，整个条走完需 0.7秒
        self.tick_duration = 0.1 
        self.look_ahead_time = 7 * self.tick_duration # 提前 7*x 时间出现
        
        # 判定窗口 (秒)
        self.hit_window = 0.3 

        # --- 预处理乐谱 (把时长转换为绝对时间轴) ---
        self.timeline = [] # 存储处理后的步数据
        self._preprocess_song()
        
        # --- 运行时状态 --- 
        self.start_time = 0.0
        self.current_step_index = 0
        self.active_note = None # 当前正在播放的音符

    def _preprocess_song(self):
        """
        把 songs.py 里的相对时长 (Duration) 转换为绝对时间戳 (Start Time)。
        结构: {'note': 'C4', 'start': 0.0, 'end': 0.4, 'move': MOVE_ID, 'hit': False}
        """
        current_time = 0.0
        bpm_scale = self.song_data.get("bpm_scale", 1.0)
        
        for note_name, duration, move_id in self.song_data["steps"]:
            real_duration = duration * bpm_scale
            self.timeline.append({
                "note": note_name,
                "start": current_time,
                "end": current_time + real_duration,
                "move": move_id,
                "hit_processed": False # 标记该音符是否已经被处理（得分或Miss）
            })
            current_time += real_duration
            
        self.total_duration = current_time

    def start(self):
        """开始游戏，记录启动时间"""
        self.start_time = time.monotonic()
        self.score = 0
        self.hw.display_text(f"Score: {self.score}", scale=2)
        print(f"Game Started! Total Duration: {self.total_duration:.2f}s")

    def update(self):
        """
        核心帧循环函数：这一帧要做什么？
        1. 计算当前音乐时间
        2. 更新蜂鸣器 (播放/静音)
        3. 计算并更新 NeoPixel 灯光位置
        4. 检测用户输入并计分
        """
        if self.is_game_over or self.is_won:
            return

        now = time.monotonic()
        song_time = now - self.start_time

        # --- 1. 检查游戏结束/胜利 ---
        if song_time > self.total_duration + 1.0: # 多给1秒缓冲
            self.is_won = True
            return

        # --- 2. 音频逻辑 (Audio) ---
        # 找到当前应该播放的音符
        # 我们遍历 timeline，找到 start <= song_time < end 的那个音符
        playing_note = None
        for step in self.timeline:
            if step["start"] <= song_time < step["end"]:
                playing_note = step
                break
        
        if playing_note:
            # 如果是新音符或者是同一个音符但还没结束
            freq = self._get_note_freq(playing_note["note"])
            # 直接操作硬件底层 (非阻塞)
            if freq > 0:
                self.hw.buzzer.frequency = freq
                self.hw.buzzer.duty_cycle = 49152 # ON
            else:
                self.hw.buzzer.duty_cycle = 65535 # Silence
        else:
            self.hw.buzzer.duty_cycle = 65535 # Silence

        # --- 3. 灯光算法 (Visuals) ---
        self.hw.pixels.fill((0, 0, 0)) # 清空当前帧

        # 遍历所有步骤，寻找那些在 "未来窗口" 内的音符
        for step in self.timeline:
            move_id = step["move"]
            target_time = step["start"] # 音符开始的时间即为打击点
            
            # 算法核心: 判断是否在显示区间内
            # 如果 (target_time - 7x) < song_time < target_time
            time_until_hit = target_time - song_time
            
            if 0 <= time_until_hit <= self.look_ahead_time:
                if move_id == settings.MOVE_NONE: continue

                # 计算灯珠位置 (0到6)
                # time_until_hit 越小 (越接近0)，位置应该越靠近终点 (Index 6)
                # 比例 ratio 从 0 (刚出现) 到 1 (到达终点)
                ratio = 1.0 - (time_until_hit / self.look_ahead_time)
                pixel_index = int(ratio * 7) # 0, 1, ..., 6
                
                # 限制范围防止溢出
                pixel_index = max(0, min(6, pixel_index))
                
                # 获取该动作对应的颜色和行号
                self._draw_note_on_strip(move_id, pixel_index)

        self.hw.pixels.show() # 刷新灯带

        # --- 4. 输入判定逻辑 (Input & Scoring) ---
        user_input = self.hw.read_game_inputs()
        
        if user_input != settings.MOVE_NONE:
            # 玩家做了动作，检查是否有音符在判定窗口内
            hit_step = None
            
            for step in self.timeline:
                # 判定窗口: 音符开始时间的前后 hit_window 秒
                # 且该音符必须还没被处理过 (hit_processed == False)
                if abs(step["start"] - song_time) < self.hit_window:
                    if not step["hit_processed"] and step["move"] != settings.MOVE_NONE:
                        hit_step = step
                        break
            
            if hit_step:
                # 检查动作是否匹配
                if user_input == hit_step["move"]:
                    # HIT!
                    self.score += 10
                    hit_step["hit_processed"] = True
                    print(f"HIT! Score: {self.score}")
                    self.hw.display_text(f"Score: {self.score}", scale=2)
                    # 可以在这里加一个瞬时的绿色闪光效果
                else:
                    # WRONG MOVE!
                    print(f"WRONG MOVE! Expected {hit_step['move']}, got {user_input}")
                    self.is_game_over = True # 或者扣分
            else:
                # 玩家在没有音符的时候乱动 -> 可以选择忽略或扣分
                pass

        # 检查 Miss (漏键)
        # 如果当前时间已经超过了 (step.start + window)，且还没处理，且不是休息音符
        for step in self.timeline:
            if song_time > (step["start"] + self.hit_window) and not step["hit_processed"]:
                if step["move"] != settings.MOVE_NONE:
                    print("MISS!")
                    step["hit_processed"] = True # 标记为已处理(Miss)
                    self.is_game_over = True # 严格模式：漏键即死

    # --- 辅助函数 ---
    
    def _get_note_freq(self, note_name):
        from songs import NOTES
        return NOTES.get(note_name, 0)

    def _draw_note_on_strip(self, move_id, local_index):
        """
        根据动作ID和段内索引 (0-6)，点亮对应的绝对位置灯珠。
        """
        base_index = 0
        color = (255, 255, 255) # 默认白

        if move_id == settings.MOVE_TOUCH_1:
            base_index = 0   # Row 1: 0-6
            color = (255, 0, 0) # Red
        elif move_id == settings.MOVE_TOUCH_2:
            base_index = 7   # Row 2: 7-13
            # 注意: 根据 neo_test.py，第二行可能是物理反向，
            # 但我们在逻辑上假设 index 0 是起始点。
            # 如果需要视觉上的“下落”，可能需要根据灯带物理走线调整:
            # 如果是蛇形走线，偶数行可能需要 inverted_index = 6 - local_index
            local_index = 6 - local_index # 假设蛇形走线反向
            color = (0, 255, 0) # Green
        elif move_id == settings.MOVE_TOUCH_3:
            base_index = 14  # Row 3: 14-20
            color = (0, 0, 255) # Blue
        elif move_id == settings.MOVE_TOUCH_4:
            base_index = 21  # Row 4: 21-27
            local_index = 6 - local_index # 假设蛇形走线反向
            color = (255, 255, 0) # Yellow
        elif move_id == settings.MOVE_TAP:
            # Double Tap: 让所有行同时亮，或者闪烁特殊色
            # 这里简单处理：显示在第一行紫色
            base_index = 0
            color = (255, 0, 255)
        elif move_id == settings.MOVE_LEFT:
             # Tilt Left: 显示在最后一行青色
            base_index = 21
            color = (0, 255, 255)

        # 计算绝对索引
        final_pixel = base_index + local_index
        
        if 0 <= final_pixel < settings.NUM_PIXELS:
            self.hw.pixels[final_pixel] = color