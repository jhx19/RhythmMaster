import time
import settings

class RhythmGame:
    def __init__(self, hardware, song_data):
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
        self.tick_duration = 0.1 
        self.look_ahead_time = 7 * self.tick_duration 
        
        # Perfect 判定区: 在时间中点的前后多少秒内算 Perfect
        # 默认为 0.15秒，可根据难度调整
        self.perfect_window = 0.15

        # --- 乐谱预处理 ---
        self.timeline = [] 
        self._preprocess_song_windows()
        
        # --- 运行时状态 ---
        self.start_time = 0.0
        self.active_index = 0 # 当前时间指针指向的音符索引

    def _preprocess_song_windows(self):
        """
        基于【时间切片法】预处理窗口。
        每个音符拥有一段专属时间窗口：
        Start = (Prev_Time + Curr_Time) / 2
        End   = (Curr_Time + Next_Time) / 2
        """
        bpm_scale = self.song_data.get("bpm_scale", 1.0)
        raw_steps = self.song_data["steps"]
        total_steps = len(raw_steps)
        
        current_play_time = 0.0
        
        # 第一遍：生成绝对时间点
        temp_timeline = []
        for note_name, duration, move_input in raw_steps:
            real_duration = duration * bpm_scale
            
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
        self.hw.display_text(f"Ready?", scale=2)
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


        # 4. 输入处理 (Input Handling) - 极简逻辑
        user_input = self.hw.read_game_inputs()
        
        # 只有在有输入，且当前音符需要操作时才判定
        if user_input != settings.MOVE_NONE and len(active_node["required_moves"]) > 0:
            
            # 检查用户输入是否在当前音符的需求列表中
            if user_input in active_node["required_moves"]:
                # --- 命中逻辑 (HIT) ---
                
                # A. 从需求集合中移除该操作 (支持组合键，按对一个消一个)
                active_node["required_moves"].remove(user_input)
                
                # B. 判定 Perfect 还是 Good
                # 计算绝对误差
                diff = abs(song_time - active_node["target_time"])
                is_perfect = diff <= self.perfect_window
                
                points = 20 if is_perfect else 10
                hit_type = "PERFECT" if is_perfect else "GOOD"
                
                # C. 如果所有需求都完成了 (集合空了)，才算彻底完成
                if len(active_node["required_moves"]) == 0:
                    self.score += points
                    self.combo += 1
                    self.max_combo = max(self.max_combo, self.combo)
                    active_node["hit_status"] = "HIT"
                    
                    # 视觉反馈
                    print(f"{hit_type}! Score: {self.score}")
                    self.hw.display_text(f"{hit_type}\n{self.combo}", scale=2)
                    self._flash_row(user_input)
                else:
                    # 还有剩下的操作没做 (例如双按只按了一个)，暂不加分，等待另一个
                    print("Combo Hit Part 1...")
            
            else:
                # --- 错误输入 (Wrong Move) ---
                # 按你的要求：直接忽略 (Pass)
                # 不扣分，不断连，不结束游戏
                # print(f"Ignored input: {user_input}")
                pass

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
        # 复制之前正确的蛇形走线绘制逻辑
        target_pixel = -1
        color = (50, 50, 50) 

        if move_id == settings.MOVE_TOUCH_1:
            target_pixel = 0 + local_pos
            color = (255, 0, 0)
        elif move_id == settings.MOVE_TOUCH_2:
            target_pixel = 13 - local_pos
            color = (0, 255, 0)
        elif move_id == settings.MOVE_TOUCH_3:
            target_pixel = 14 + local_pos
            color = (0, 0, 255)
        elif move_id == settings.MOVE_TOUCH_4:
            target_pixel = 27 - local_pos
            color = (255, 255, 0)
        elif move_id == settings.MOVE_TAP:
            target_pixel = 0 + local_pos
            color = (255, 0, 255)
        elif move_id == settings.MOVE_LEFT:
             target_pixel = 27 - local_pos
             color = (0, 255, 255)

        if 0 <= target_pixel < settings.NUM_PIXELS:
            self.hw.pixels[target_pixel] = color