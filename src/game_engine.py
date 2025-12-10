import time
import settings

class RhythmGame:
    def __init__(self, hardware, song_data, difficulty=settings.DIFFICULTY_EASY):
        self.hw = hardware
        self.song_data = song_data
        
        # --- 游戏参数 ---
        self.score = 0
        self.combo = 0 
        self.max_combo = 0
        self.is_game_over = False
        self.is_won = False
        
        # 视觉参数
        self.tick_duration = settings.DURATION[difficulty]
        self.look_ahead_time = 7 * self.tick_duration 
        self.bpm_scale = settings.BPM[difficulty]
        self.score_factor = settings.SCORE_FACTOR[difficulty]   
        
        # --- 判定窗口逻辑 (Fixed Beat Window) ---
        # 基础短音符时长 (Quarter Note) 默认为 0.4s (参考 songs.py)
        # 实际时长根据难度系数缩放
        base_qn_duration = settings.QN * self.bpm_scale
        
        # Good Window: 允许误差为短音符时长的一半 (+/-)
        # 这样 Good 判定区总宽度等于一个短音符时长，覆盖了整个节拍
        self.good_window = base_qn_duration / 2.5
        
        # Perfect Window: Good 窗口的一半
        self.perfect_window = self.good_window / 2.0
        
        print(f"Difficulty: {settings.DIFFICULTY_NAMES[difficulty]}")
        print(f"Beat Duration: {base_qn_duration:.3f}s")
        print(f"Windows -> Good: +/-{self.good_window:.3f}s, Perfect: +/-{self.perfect_window:.3f}s")

        # --- 乐谱预处理 ---
        self.timeline = [] 
        self._preprocess_song_windows()
        
        # --- 运行时状态 ---
        self.start_delay = 2.0  # 开局下落缓冲
        self.start_time = 0.0
        self.active_index = 0   
        self.audio_index = 0    
        
        # 非阻塞音频控制
        self.current_buzzer_end_time = 0.0

        # 颜色定义
        self.COLOR_NICE_GREEN = settings.COLOR_NICE_GREEN
        self.COLOR_NICE_RED   = settings.COLOR_NICE_RED
        self.GRADIENT_BLUE = settings.GRADIENT_BLUE

    def _preprocess_song_windows(self):
        """
        基于【固定节拍窗口】预处理。
        不再依赖前后音符的中点，而是依赖固定的 BPM 窗口。
        """
        raw_steps = self.song_data["steps"]
        total_steps = len(raw_steps)
        
        current_play_time = 0.0
        
        # 生成时间轴
        for note_name, duration, move_input in raw_steps:
            real_duration = duration * self.bpm_scale
            freq = self._get_note_freq(note_name)
            
            # 处理多按键
            if isinstance(move_input, list):
                moves_set = set(move_input)
            else:
                moves_set = {move_input} if move_input != settings.MOVE_NONE else set()

            # 计算窗口结束时间 (用于判定 MISS)
            # 超过 Target Time + Good Window 即视为 Miss
            target_t = current_play_time
            win_start_t = target_t - self.good_window
            win_end_t = target_t + self.good_window

            self.timeline.append({
                "note": note_name,
                "freq": freq,
                "target_time": target_t,
                "duration": real_duration,
                "win_start": win_start_t,
                "win_end": win_end_t,    
                "required_moves": moves_set,     
                "total_moves_count": len(moves_set),
                "hit_status": "NONE"             
            })
            current_play_time += real_duration
            
        self.total_duration = current_play_time

    def _get_note_freq(self, note_name):
        from songs import NOTES
        return NOTES.get(note_name, 0)

    def start(self):
        self.start_time = time.monotonic() + self.start_delay
        self.active_index = 0
        self.audio_index = 0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.hw.set_leds((0, 0, 0))
        
        self.hw.display_text("GET READY", scale=2, y_offset=25)

    def update(self):
        if self.is_game_over or self.is_won:
            return

        now = time.monotonic()
        song_time = now - self.start_time

        # 1. 胜利检查
        if song_time > self.total_duration + 1.0:
            self.is_won = True
            self._stop_tone()
            return

        # 2. 音频更新
        self._update_audio(song_time, now)

        # 3. Miss 判定与指针移动
        # 只要当前时间超过了 active_index 的 [target + good_window]，说明错过了
        while self.active_index < len(self.timeline):
            current_node = self.timeline[self.active_index]
            
            if song_time > current_node["win_end"]:
                # 窗口结束，若仍有未完成动作 -> MISS
                if len(current_node["required_moves"]) > 0:
                    print(f"MISS at index {self.active_index}!")
                    current_node["hit_status"] = "MISS"
                    self.combo = 0 
                    self._draw_hud("MISS")
                
                self.active_index += 1
            else:
                # 还在窗口内（或者还没到窗口），停止移动指针
                break

        # 4. 视觉更新
        self._update_visuals(song_time)

        # 5. 输入处理
        self._handle_input(song_time)

    def _update_audio(self, song_time, now_absolute):
        if now_absolute >= self.current_buzzer_end_time:
            self._stop_tone()

        while self.audio_index < len(self.timeline):
            node = self.timeline[self.audio_index]
            if song_time >= node["target_time"]:
                if node["freq"] > 0:
                    play_len = min(node["duration"] * 0.9, 0.5) 
                    self._start_tone(node["freq"])
                    self.current_buzzer_end_time = now_absolute + play_len
                self.audio_index += 1
            else:
                break

    def _start_tone(self, freq):
        if self.hw.buzzer:
            self.hw.buzzer.frequency = freq
            self.hw.buzzer.duty_cycle = 49152 

    def _stop_tone(self):
        if self.hw.buzzer:
            self.hw.buzzer.duty_cycle = 65535 

    def _handle_input(self, song_time):
        user_input = self.hw.read_game_inputs()
        
        if user_input == settings.MOVE_NONE:
            return

        # 只有 active_index 是合法的判定对象
        if self.active_index < len(self.timeline):
            active_node = self.timeline[self.active_index]
            
            # 计算时间差绝对值
            diff = abs(song_time - active_node["target_time"])
            
            # 只有在 Good Window 内才响应 
            if diff <= self.good_window:
                if user_input in active_node["required_moves"]:
                    # --- 命中 ---
                    active_node["required_moves"].remove(user_input)
                    
                    # 判定是否是 Perfect 
                    is_perfect = diff <= self.perfect_window
                    
                    base_points = 20 if is_perfect else 10
                    self.score += base_points * self.score_factor
                    
                    hit_type = "PERFECT" if is_perfect else "GOOD"
                    
                    # 全部动作完成处理
                    if len(active_node["required_moves"]) == 0:
                        self.combo += 1
                        self.max_combo = max(self.max_combo, self.combo)
                        active_node["hit_status"] = "HIT"
                        
                        if self.combo > 2:
                            self.score += 5 

                    self._draw_hud(hit_type)
                    self._flash_row(user_input)
                else:
                    # 只有按对键才算，按错键忽略（不打断Combo，也不加分）
                    pass

    def _draw_hud(self, feedback_text=""):
        layers = [
            {'text': f"Score: {int(self.score)}", 'scale': 1, 'y': 5, 'x': 5}
        ]
        
        if feedback_text:
            layers.append({'text': feedback_text, 'scale': 2, 'y': 32})
            
        if self.combo > 2:
            layers.append({'text': f"Combo: {self.combo}", 'scale': 1, 'y': 58})

        self.hw.display_layers(layers)

    def _update_visuals(self, song_time):
        self.hw.pixels.fill((0, 0, 0))
        
        start_idx = self.active_index
        end_idx = min(len(self.timeline), self.active_index + 10)

        for i in range(start_idx, end_idx):
            step = self.timeline[i]
            
            if step["hit_status"] == "HIT" or len(step["required_moves"]) == 0:
                continue
            
            if step["total_moves_count"] == 0:
                continue

            time_until_hit = step["target_time"] - song_time
            
            if 0 <= time_until_hit <= self.look_ahead_time:
                ratio = 1.0 - (time_until_hit / self.look_ahead_time)
                local_pos = int(ratio * 7)
                local_pos = max(0, min(6, local_pos))
                
                display_move = list(step["required_moves"])[0]
                self._draw_note_smart(display_move, local_pos)
        
        self.hw.pixels.show()

    def _draw_note_smart(self, move_id, local_pos):
        def get_physical_index(track_idx, vis_pos):
            if track_idx == 0: return 0 + vis_pos
            if track_idx == 1: return 13 - vis_pos
            if track_idx == 2: return 14 + vis_pos
            if track_idx == 3: return 27 - vis_pos
            return -1

        pixels_to_light = []

        if move_id in [settings.MOVE_TAP, settings.MOVE_LEFT, settings.MOVE_RIGHT]:
            for t_idx in range(4):
                phys_idx = get_physical_index(t_idx, local_pos)
                if phys_idx < 0: continue
                
                color = self.COLOR_NICE_RED 
                
                if move_id == settings.MOVE_LEFT:
                    color = self.GRADIENT_BLUE[t_idx]
                elif move_id == settings.MOVE_RIGHT:
                    color = self.GRADIENT_BLUE[3 - t_idx]
                
                pixels_to_light.append((phys_idx, color))

        elif move_id in [settings.MOVE_TOUCH_1, settings.MOVE_TOUCH_2, settings.MOVE_TOUCH_3, settings.MOVE_TOUCH_4]:
            target_track = 0
            if move_id == settings.MOVE_TOUCH_2: target_track = 1
            if move_id == settings.MOVE_TOUCH_3: target_track = 2
            if move_id == settings.MOVE_TOUCH_4: target_track = 3
            
            phys_idx = get_physical_index(target_track, local_pos)
            if phys_idx >= 0:
                pixels_to_light.append((phys_idx, self.COLOR_NICE_GREEN))

        for p_idx, color_val in pixels_to_light:
            if 0 <= p_idx < settings.NUM_PIXELS:
                self.hw.pixels[p_idx] = color_val

    def _flash_row(self, move_id):
        pass
