import time
import settings

class RhythmGame:
    def __init__(self, hardware, song_data, difficulty=settings.DIFFICULTY_EASY):
        self.hw = hardware
        self.song_data = song_data
        
        # --- 游戏参数 ---
        self.score = 0
        self.combo = 0 # 连击数
        self.max_combo = 0
        self.is_game_over = False
        self.is_won = False
        
        # 视觉参数: 决定灯珠流动的速度
        # 难度越高，Tick 越短，流动越快
        self.tick_duration = settings.DURATION[difficulty]
        self.look_ahead_time = 7 * self.tick_duration 

        # BPM 系数，用于调整音符速度
        self.bpm_scale = settings.BPM[difficulty]

        # 分数倍率，根据难度调整
        self.score_factor = settings.SCORE_FACTOR[difficulty]   
        
        # Perfect 判定区: 在时间中点的前后多少秒内算 Perfect
        # 默认为 0.15秒，可根据难度调整
        self.perfect_window = 0.15

        # --- 乐谱预处理 ---
        self.timeline = [] 
        self._preprocess_song_windows()
        
        # --- 运行时状态 ---
        self.start_time = 0.0
        self.active_index = 0 # 当前时间指针指向的音符索引

        # 柔和的颜色定义 (R, G, B)
        self.COLOR_NICE_GREEN = settings.COLOR_NICE_GREEN    # 更饱和的绿色 (Touch)
        self.COLOR_NICE_RED   = settings.COLOR_NICE_RED      # 柔和红 (Double Tap)
    
    # 蓝色渐变阶梯 (从深到浅)
    # 用于 Left/Right Tilt 的四条轨道分配
        self.GRADIENT_BLUE = settings.GRADIENT_BLUE

    def _preprocess_song_windows(self):
        """
        基于【时间切片法】预处理窗口。
        每个音符拥有一段专属时间窗口：
        Start = (Prev_Time + Curr_Time) / 2
        End   = (Curr_Time + Next_Time) / 2
        """
        raw_steps = self.song_data["steps"]
        total_steps = len(raw_steps)
        
        current_play_time = 0.0
        
        # 第一遍：生成绝对时间点
        temp_timeline = []
        for note_name, duration, move_input in raw_steps:
            real_duration = duration * self.bpm_scale
            
            # 处理多按键逻辑: 如果 move_input 是列表就转集合，是单个就转单元素集合
            # 例如: move_input = [TOUCH1, TOUCH2] -> {1, 2}
            if isinstance(move_input, list):
                moves_set = set(move_input)
            else:
                moves_set = {move_input} if move_input != settings.MOVE_NONE else set()

            temp_timeline.append({
                "note": note_name,
                "target_time": current_play_time, # 音乐播放时刻 (打击点)
                "duration": real_duration,
                "required_moves": moves_set,      # 剩余需要完成的操作集合
                "total_moves_count": len(moves_set),
                "hit_status": "NONE"              # NONE, HIT, MISS
            })
            current_play_time += real_duration
            
        self.total_duration = current_play_time

        # 第二遍：计算判定窗口 (Window Start/End)
        for i in range(total_steps):
            curr_node = temp_timeline[i]
            curr_t = curr_node["target_time"]
            
            # 计算窗口起点 (Window Start)
            if i == 0:
                # 第一个音符，起点设为 0 或者稍微提前一点
                curr_node["win_start"] = curr_t - 0.5 # 给首音符0.5s准备
            else:
                prev_t = temp_timeline[i-1]["target_time"]
                curr_node["win_start"] = (prev_t + curr_t) / 2.0
            
            # 计算窗口终点 (Window End)
            if i == total_steps - 1:
                # 最后一个音符，终点设为结束时间 + 缓冲
                curr_node["win_end"] = curr_t + curr_node["duration"]
            else:
                next_t = temp_timeline[i+1]["target_time"]
                curr_node["win_end"] = (curr_t + next_t) / 2.0
                
            self.timeline.append(curr_node)

    def start(self):
        self.start_time = time.monotonic()
        self.active_index = 0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.hw.set_leds((0, 0, 0))
        
        # 调用新的 HUD 绘制函数
        self.hw.display_text("GET READY", scale=2, y_offset=25)
        print("Game Started using Time Slicing Logic")

    def update(self):
        if self.is_game_over or self.is_won:
            return

        now = time.monotonic()
        song_time = now - self.start_time

        # 1. 游戏结束检查
        if song_time > self.total_duration + 1.0:
            self.is_won = True
            return

        # 2. 更新当前活跃音符指针 (Active Pointer)
        # 只要当前时间超过了 active_index 的窗口终点，就说明这个音符的时间过去了
        # 我们需要移动指针到下一个
        while self.active_index < len(self.timeline):
            current_node = self.timeline[self.active_index]
            
            if song_time > current_node["win_end"]:
                # 窗口结束时的结算逻辑:
                # 如果这个音符需要操作(required_moves不为空)，且还没被清空，那就是 MISS
                if len(current_node["required_moves"]) > 0:
                    print(f"MISS at index {self.active_index}!")
                    current_node["hit_status"] = "MISS"
                    self.combo = 0 # 断连
                    self.hw.display_text("MISS", scale=2)
                    # 注意：按你的要求，Miss 不导致 Game Over，只重置 Combo 或不加分
                    # 如果要严格模式，这里置 self.is_game_over = True
                
                self.active_index += 1
            else:
                # 还没出窗口，停止移动指针
                break

        # 安全检查: 防止索引越界
        if self.active_index >= len(self.timeline):
            return

        # 获取当前正在判定区间的音符
        active_node = self.timeline[self.active_index]

        # 3. 视觉与音频处理 (保持之前的逻辑，略作适配)
        self._update_feedback(song_time)


        # 4. 输入处理
        user_input = self.hw.read_game_inputs()
        
        # 获取当前正在判定区间的音符
        if self.active_index < len(self.timeline):
            active_node = self.timeline[self.active_index]
            
            if user_input != settings.MOVE_NONE and len(active_node["required_moves"]) > 0:
                if user_input in active_node["required_moves"]:
                    # --- 命中逻辑 ---
                    active_node["required_moves"].remove(user_input)
                    
                    # 判定 Perfect/Good
                    diff = abs(song_time - active_node["target_time"])
                    is_perfect = diff <= self.perfect_window
                    
                    points = 20 * self.score_factor if is_perfect else 10 * self.score_factor
                    hit_type = "PERFECT" if is_perfect else "GOOD"
                    
                    if len(active_node["required_moves"]) == 0:
                        self.score += points
                        self.combo += 1
                        self.max_combo = max(self.max_combo, self.combo)
                        # 连击奖励，每增加一次连击，额外加5分
                        if self.combo > 2:
                            self.score += 5 * self.score_factor

                        active_node["hit_status"] = "HIT"
                        
                        # --- 更新 HUD: 显示 PERFECT/GOOD ---
                        self._draw_hud(hit_type)
                        
                        self._flash_row(user_input)
                else:
                    # 错误输入忽略，不刷新屏幕
                    pass

    def _draw_hud(self, feedback_text=""):
        """
        根据用户要求绘制游戏界面 (HUD):
        - Top: Score (Scale 1)
        - Mid: PERFECT/GOOD/MISS (Scale 2)
        - Bot: Combo (Scale 1, only if > 2)
        """
        layers = []
        
        # 1. Top: Score (屏幕上方 y=5)
        # 显示格式 "Score: 120"
        layers.append({
            'text': f"Score: {self.score}", 
            'scale': 1, 
            'y': 5,
            'x': 5 # 左对齐
        })
        
        # 2. Middle: Feedback (屏幕正中 y=32)
        # 显示格式 "PERFECT" / "MISS"
        if feedback_text:
            layers.append({
                'text': feedback_text, 
                'scale': 2, 
                'y': 32 
                # x 默认居中 (在 hardware.py 中处理)
            })
            
        # 3. Bottom: Combo (屏幕下方 y=58)
        # 只有连击数 > 2 时才显示
        if self.combo > 2:
            layers.append({
                'text': f"Combo: {self.combo}", 
                'scale': 1, 
                'y': 58 
                # x 默认居中
            })

        # 提交给硬件层绘制
        self.hw.display_layers(layers)

    def _update_feedback(self, song_time):
        """负责音频播放和灯光绘制"""
        self.hw.pixels.fill((0, 0, 0))
        
        # 音频逻辑
        # 简单判定: 哪个音符的 target_time 在附近就播哪个 (简化版)
        # 或者沿用之前区间逻辑，这里为了简洁省略具体音频重写，
        # 建议保留你之前的音频区间判断逻辑。
        
        # 灯光逻辑
        # 依然需要遍历未来几个音符来绘制
        for i in range(self.active_index, min(len(self.timeline), self.active_index + 6)):
            step = self.timeline[i]
            
            # 如果已经打完了，就不显示了
            if step["hit_status"] == "HIT":
                continue
                
            # 只有有操作需求的才绘制
            if step["total_moves_count"] == 0:
                continue

            # 计算视觉位置
            # 这里的逻辑不变: 根据 target_time 和 look_ahead 倒推
            time_until_hit = step["target_time"] - song_time
            
            if 0 <= time_until_hit <= self.look_ahead_time:
                ratio = 1.0 - (time_until_hit / self.look_ahead_time)
                pixel_index = int(ratio * 7)
                pixel_index = max(0, min(6, pixel_index))
                
                # 获取该音符原始需要的动作 (即便现在被消掉了一个，显示时最好还是显示主动作)
                # 这里简单取第一个动作来决定颜色
                # 注意: 因为 required_moves 是动态变化的，我们可能需要 step 存一个 immutable 的原始动作
                # 但这里为了简单，我们假设组合键通常颜色混合或者只显示主色
                if len(step["required_moves"]) > 0:
                    primary_move = list(step["required_moves"])[0] 
                    self._draw_note_smart(primary_move, pixel_index)
        
        self.hw.pixels.show()

    def _flash_row(self, move_id):
        # 简易实现：让硬件类负责闪烁，或者这里直接给灯带赋值
        pass

    def _draw_note_smart(self, move_id, local_pos):
        """
        根据 move_id 和 local_pos (0-6) 绘制灯光。
        支持特殊动作全轨道显示和渐变色。
        """
        
        # 1. 定义一个内部帮助函数：计算某条轨道在当前 visual_pos 的物理索引
        # 这是你之前的正确逻辑
        def get_physical_index(track_idx, vis_pos):
            if track_idx == 0: return 0 + vis_pos
            if track_idx == 1: return 13 - vis_pos
            if track_idx == 2: return 14 + vis_pos
            if track_idx == 3: return 27 - vis_pos
            return -1

        # 2. 初始化要点亮的像素列表： [(pixel_index, color), ...]
        pixels_to_light = []

        # --- 情况 A: 特殊动作 (全轨道显示) ---
        if move_id in [settings.MOVE_TAP, settings.MOVE_LEFT, settings.MOVE_RIGHT]:
            
            # 遍历所有 4 条轨道
            for t_idx in range(4):
                phys_idx = get_physical_index(t_idx, local_pos)
                if phys_idx < 0: continue
                
                # 确定颜色
                if move_id == settings.MOVE_TAP:
                    # Double Tap: 全红
                    c = self.COLOR_NICE_RED
                
                elif move_id == settings.MOVE_LEFT:
                    # Left: 从左到右 -> 深蓝到浅蓝
                    # T0(深) -> T1 -> T2 -> T3(浅)
                    c = self.GRADIENT_BLUE[t_idx]
                    
                elif move_id == settings.MOVE_RIGHT:
                    # Right: 从左到右 -> 浅蓝到深蓝
                    # T0(浅) -> T1 -> T2 -> T3(深)
                    # 也就是把渐变列表倒过来取
                    c = self.GRADIENT_BLUE[3 - t_idx]
                
                pixels_to_light.append((phys_idx, c))

        # --- 情况 B: 普通 Touch (单轨道显示) ---
        elif move_id in [settings.MOVE_TOUCH_1, settings.MOVE_TOUCH_2, settings.MOVE_TOUCH_3, settings.MOVE_TOUCH_4]:
            
            target_track = -1
            if move_id == settings.MOVE_TOUCH_1: target_track = 0
            if move_id == settings.MOVE_TOUCH_2: target_track = 1
            if move_id == settings.MOVE_TOUCH_3: target_track = 2
            if move_id == settings.MOVE_TOUCH_4: target_track = 3
            
            phys_idx = get_physical_index(target_track, local_pos)
            if phys_idx >= 0:
                # 统一使用好看的绿色
                pixels_to_light.append((phys_idx, self.COLOR_NICE_GREEN))

        # 3. 执行绘制
        for p_idx, color_val in pixels_to_light:
            if 0 <= p_idx < settings.NUM_PIXELS:
                # 注意：这里直接赋值。如果多个音符重叠，后绘制的会覆盖先绘制的。
                # 如果希望颜色混合，可以做复杂的 add logic，但通常直接覆盖在节奏游戏中更清晰。
                self.hw.pixels[p_idx] = color_val