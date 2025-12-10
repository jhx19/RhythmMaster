import time
import board
import microcontroller
import struct
import settings
import songs
from hardware import HardwareManager
from game_engine import RhythmGame

# --- 全局状态常量 ---
STATE_SPLASH = 0
STATE_MENU_DIFFICULTY = 1
STATE_MENU_LEVEL = 2
STATE_PLAYING = 3
STATE_GAME_OVER = 4
STATE_HIGHSCORE_ENTRY = 5
STATE_HIGHSCORE_VIEW = 6

# --- 排行榜管理类 (基于 NVM) ---
# --- 排行榜管理类 (基于 NVM) ---
class HighScoreManager:
    # NVM 布局: 
    # Header (2 bytes): 修改 Header 值以强制重置旧数据 (例如改最后一位)
    # Records (6条): 每条 7 bytes (3 bytes 名字 + 4 bytes 分数 int)
    
    # [修复1] 修改 Header 比如 b'\xBE\xF1'，这会强制触发 _reset_nvm，清除以前可能出错的数据
    HEADER = b'\xBE\xF1'  
    MAX_ENTRIES = 6
    ENTRY_SIZE = 7 
    OFFSET = 0 

    def __init__(self):
        self.nvm = microcontroller.nvm
        # 检查是否初始化
        if self.nvm[0:2] != self.HEADER:
            self._reset_nvm()

    def _reset_nvm(self):
        print("Initializing High Scores...")
        self.nvm[0:2] = self.HEADER
        # 填充默认数据
        empty_data = (b'GIX', 100)
        for i in range(self.MAX_ENTRIES):
            self._write_entry(i, *empty_data)

    def _write_entry(self, index, name_bytes, score):
        start = 2 + index * self.ENTRY_SIZE
        # [修复2] 使用 '<3sI'。 '<' 强制使用标准大小(不填充)，确保它是严格的 7 bytes
        data = struct.pack('<3sI', name_bytes, score)
        self.nvm[start : start + self.ENTRY_SIZE] = data

    def get_high_scores(self):
        scores = []
        for i in range(self.MAX_ENTRIES):
            start = 2 + i * self.ENTRY_SIZE
            data = self.nvm[start : start + self.ENTRY_SIZE]
            try:
                # [修复2] 同样使用 '<3sI' 进行解包
                name, score = struct.unpack('<3sI', data)
                # 处理名字中的空字节 (如果有)
                decoded_name = name.decode('utf-8').rstrip('\x00')
                scores.append((decoded_name, score))
            except Exception as e:
                print(f"Error reading score {i}: {e}")
                scores.append(("ERR", 0))
                
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def add_score(self, name_str, score):
        current_scores = self.get_high_scores()
        current_scores.append((name_str, score))
        current_scores.sort(key=lambda x: x[1], reverse=True)
        current_scores = current_scores[:self.MAX_ENTRIES]
        
        # 写回 NVM
        for i, (n, s) in enumerate(current_scores):
            self._write_entry(i, n.encode('utf-8'), s)

# --- 主程序 ---
class GameApp:
    def __init__(self):
        self.hw = HardwareManager()
        self.hs_manager = HighScoreManager()
        self.state = STATE_SPLASH
        
        # 游戏会话数据
        self.difficulty = settings.DIFFICULTY_EASY
        self.current_level_index = 0 # 0-based index
        self.session_score = 0       # 之前关卡累积的分数
        self.current_game_engine = None
        self.last_level_score = 0    # 当前关卡获得的分数

    def run(self):
        while True:
            if self.state == STATE_SPLASH:
                self.do_splash()
            elif self.state == STATE_MENU_DIFFICULTY:
                self.do_menu_difficulty()
            elif self.state == STATE_MENU_LEVEL:
                self.do_menu_level()
            elif self.state == STATE_PLAYING:
                self.do_playing()
            elif self.state == STATE_GAME_OVER:
                self.do_game_over()
            elif self.state == STATE_HIGHSCORE_ENTRY:
                self.do_highscore_entry()
            elif self.state == STATE_HIGHSCORE_VIEW:
                self.do_highscore_view()
            
            # 全局小延时防止空转过快
            time.sleep(0.01)

    # --- 1. 开场动画 ---
    def do_splash(self):
        # 动画 1: 文字出现
        self.hw.display_layers([
            {'text': "GIX", 'scale': 3, 'y': 20},
            {'text': "RHYTHM", 'scale': 2, 'y': 50}
        ])
        self.hw.play_tone(440, 0.1)
        self.hw.play_tone(554, 0.1)
        self.hw.play_tone(659, 0.2)
        
        # 动画 2: 灯光流水
        for i in range(10):
            color = settings.GRADIENT_BLUE[i % 4]
            self.hw.pixels.fill((0,0,0))
            self.hw.set_pixel_segment(i, i+5, color)
            time.sleep(0.05)
        
        self.hw.set_leds((0,0,0))
        time.sleep(0.5)
        self.state = STATE_MENU_DIFFICULTY

    # --- 通用菜单函数 ---
    def _run_menu(self, title, items, start_idx=0):
        """
        通用的旋转编码器菜单逻辑
        返回选择的索引
        """
        selected = start_idx
        num_items = len(items)
        
        # 首次渲染
        self._render_menu(title, items, selected)
        
        while True:
            delta = self.hw.get_encoder_delta()
            if delta != 0:
                selected = (selected + delta) % num_items
                self._render_menu(title, items, selected)
                self.hw.play_tone(880, 0.05) # 导航音效

            if self.hw.is_button_pressed():
                self.hw.play_tone(1760, 0.1) # 确认音效
                return selected
            
            time.sleep(0.05)

    def _render_menu(self, title, items, selected):
        num_items = len(items)
        if num_items == 0:
            return

        # --- 1. 计算循环索引 (关键逻辑) ---
        # 使用取模运算 % 实现首尾相接
        # (selected - 1) % num_items 自动处理了 0-1 变成 -1 的情况(Python中 -1%4=3)
        idx_prev = (selected - 1) % num_items 
        idx_curr = selected
        idx_next = (selected + 1) % num_items
        
        # --- 2. 准备显示的文本 ---
        # 如果菜单项很少(比如只有1个)，防止显示重复看着别扭，可以加个判断(可选)
        # 但标准的滚轮菜单即使重复显示也是正常的
        text_prev = items[idx_prev]
        text_curr = f"> {items[idx_curr]} <" # [优化] 使用符号强调，代替过大的字号
        text_next = items[idx_next]
        
        # --- 3. 布局设置 (Fixed Layout) ---
        # 屏幕高度 64。
        # Title: y=5 (顶部)
        # Prev:  y=20 (上方选项)
        # Curr:  y=35 (中间高亮选项 - 视觉中心)
        # Next:  y=50 (下方选项)
        
        layers = [
            {'text': title, 'scale': 1, 'y': 5},
            
            # 上一项 (暗淡/普通)
            {'text': text_prev, 'scale': 1, 'y': 20},
            
            # 当前项 (居中，虽然是 Scale 1 但加了箭头修饰)
            {'text': text_curr, 'scale': 1, 'y': 35},
            
            # 下一项 (暗淡/普通)
            {'text': text_next, 'scale': 1, 'y': 50}
        ]
        
        self.hw.display_layers(layers)

    # --- 2. 难度选择 ---
    def do_menu_difficulty(self):
        # 清除累积状态
        self.session_score = 0
        
        options = ["EASY", "NORMAL", "HARD", "High Scores"]
        idx = self._run_menu("SELECT DIFFICULTY", options)
        
        if idx == 3:
            self.state = STATE_HIGHSCORE_VIEW
        else:
            self.difficulty = idx # 0, 1, 2 对应 settings.DIFFICULTY_*
            self.state = STATE_MENU_LEVEL

    # --- 3. 关卡选择 ---
    def do_menu_level(self):
        # 获取所有可用关卡
        total_songs = len(songs.SONG_LIBRARY)
        options = [f"Level {i+1}" for i in range(total_songs)]
        options.append("Back")
        
        idx = self._run_menu("SELECT LEVEL", options)
        
        if idx == len(options) - 1:
            self.state = STATE_MENU_DIFFICULTY
        else:
            self.current_level_index = idx
            self.state = STATE_PLAYING

    # --- 4. 游戏过程 ---
    def do_playing(self):
        # 1. 准备数据
        level_data = songs.get_level_data(self.current_level_index + 1)
        if not level_data:
            print("Error: No level data")
            self.state = STATE_MENU_DIFFICULTY
            return

        # 2. 初始化引擎
        self.current_game_engine = RhythmGame(self.hw, level_data, self.difficulty)
        
        # 3. 倒计时
        for i in range(3, 0, -1):
            self.hw.display_layers([
                {'text': f"Level {self.current_level_index + 1}", 'scale': 1, 'y': 10},
                {'text': str(i), 'scale': 4, 'y': 40}
            ])
            self.hw.play_tone(440, 0.1)
            time.sleep(0.8)
        
        # 4. 开始游戏循环
        self.current_game_engine.start()
        
        while True:
            # 退出检测 (长按按钮?) - 这里简化为必须玩完
            # 调用引擎更新
            self.current_game_engine.update()
            
            # 状态检查
            if self.current_game_engine.is_game_over:
                # 失败
                self.hw.play_tone(100, 0.5)
                self.state = STATE_GAME_OVER
                break
                
            if self.current_game_engine.is_won:
                # 胜利
                self.hw.play_tone(1000, 0.2)
                time.sleep(0.1)
                self.hw.play_tone(1200, 0.4)
                self.state = STATE_GAME_OVER
                break
                
            # 注意：此处不加 time.sleep，因为 game_engine 依赖高频刷新

    # --- 5. 游戏结算 ---
    def do_game_over(self):
        engine = self.current_game_engine
        is_win = engine.is_won
        self.last_level_score = int(engine.score)
        total_now = self.session_score + self.last_level_score
        
        # 显示结果屏幕
        title = "CLEARED!" if is_win else "GAME OVER"
        self.hw.display_layers([
            {'text': title, 'scale': 2, 'y': 10},
            {'text': f"Score: {self.last_level_score}", 'scale': 1, 'y': 30},
            {'text': f"Total: {total_now}", 'scale': 1, 'y': 45},
            {'text': f"Max Combo: {engine.combo}", 'scale': 1, 'y': 60}
        ])
        
        # 等待按键进入菜单
        time.sleep(1.0) # 防止误触
        while not self.hw.is_button_pressed():
            time.sleep(0.1)
            
        # 结果菜单
        menu_options = ["Retry Level", "Save & Quit"]
        
        # 只有赢了且不是最后一关才有 Next Level
        can_next = is_win and (self.current_level_index < settings.MAX_GAME_LEVELS - 1)
        # 如果还有下一关
        if can_next:
            menu_options.insert(1, "Next Level")
        
        idx = self._run_menu("RESULT MENU", menu_options)
        
        choice = menu_options[idx]
        
        if choice == "Retry Level":
            # 重玩：不增加 session score，状态回退到 PLAYING
            self.state = STATE_PLAYING
            
        elif choice == "Next Level":
            # 下一关：确认累积当前分数
            self.session_score += self.last_level_score
            self.current_level_index += 1
            self.state = STATE_PLAYING
            
        elif choice == "Save & Quit":
            # 退出：累积最终分数并保存
            self.session_score += self.last_level_score
            self.state = STATE_HIGHSCORE_ENTRY

    # --- 6. 输入名字并保存 ---
# --- 6. 输入名字并保存 ---
    def do_highscore_entry(self):
        final_score = self.session_score
        initials = [65, 65, 65] # ASCII 'A', 'A', 'A'
        cursor = 0
        
        # [修复] 增加刷新标记，首次进入设为 True
        need_refresh = True
        
        while cursor < 3:
            # 只有当数据改变时才更新屏幕
            if need_refresh:
                char_str = "".join([chr(c) for c in initials])
                # 高亮当前字符
                indicator = " " * cursor + "^" + " " * (2-cursor)
                
                self.hw.display_layers([
                    {'text': "NEW RECORD!", 'scale': 1, 'y': 10},
                    {'text': f"Score: {final_score}", 'scale': 1, 'y': 25},
                    {'text': char_str, 'scale': 3, 'y': 45},
                    {'text': indicator, 'scale': 2, 'y': 60} 
                ])
                need_refresh = False # 重置标记

            # 输入逻辑
            delta = self.hw.get_encoder_delta()
            if delta != 0:
                initials[cursor] += delta
                if initials[cursor] > 90: initials[cursor] = 65
                if initials[cursor] < 65: initials[cursor] = 90
                need_refresh = True # [修复] 数据变了，需要刷新
            
            if self.hw.is_button_pressed():
                self.hw.play_tone(1760, 0.1)
                cursor += 1
                need_refresh = True # [修复] 光标变了，需要刷新
                time.sleep(0.2) # 防抖
            
            time.sleep(0.05)
            
        # 保存
        name = "".join([chr(c) for c in initials])
        self.hs_manager.add_score(name, final_score)
        
        self.hw.display_layers([
            {'text': "SAVED!", 'scale': 3, 'y': 32}
        ])
        time.sleep(1.5)
        self.state = STATE_HIGHSCORE_VIEW

    # --- 7. 查看排行榜 ---
    def do_highscore_view(self):
        scores = self.hs_manager.get_high_scores()
        
        # 将分数转换为菜单项只用于显示
        items = []
        for i, (name, s) in enumerate(scores):
            items.append(f"{i+1}. {name}  {s}")
            
        items.append("[ Back ]")
        
        self._run_menu("HIGH SCORES", items)
        
        # 返回主菜单
        self.state = STATE_MENU_DIFFICULTY

# --- 启动 ---
if __name__ == "__main__":
    game = GameApp()
    game.run()

