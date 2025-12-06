import time
import board
import settings
from hardware import HardwareManager
from game_engine import RhythmGame
import songs
from highscore import HighScoreManager

# --- 全局状态机常量 ---
STATE_SPLASH = 0
STATE_MENU_DIFFICULTY = 1
STATE_GAME_INIT = 2
STATE_GAME_PLAYING = 3
STATE_ROUND_RESULT = 4  # 单关结束（成功）
STATE_GAME_OVER = 5     # 关卡失败
STATE_HIGHSCORE_INPUT = 6
STATE_HIGHSCORE_VIEW = 7
STATE_ALL_CLEAR = 8     # 通关所有10关

class GameApp:
    def __init__(self):
        self.hw = HardwareManager()
        self.hs_manager = HighScoreManager()
        
        self.current_state = STATE_SPLASH
        
        # 游戏进程变量
        self.difficulty = settings.DIFFICULTY_EASY
        self.current_level = 1
        self.total_score = 0      # 累计总分
        self.last_level_score = 0 # 当前关卡得分（用于重试时回滚）
        self.current_game_engine = None
        
        # 菜单相关
        self.menu_index = 0
        self.last_interaction = time.monotonic()

    def run(self):
        while True:
            self._handle_state()
            time.sleep(0.01) # 防止死循环占用过多资源

    def _handle_state(self):
        if self.current_state == STATE_SPLASH:
            self._do_splash()
        elif self.current_state == STATE_MENU_DIFFICULTY:
            self._do_menu_difficulty()
        elif self.current_state == STATE_GAME_INIT:
            self._do_game_init()
        elif self.current_state == STATE_GAME_PLAYING:
            self._do_game_playing()
        elif self.current_state == STATE_ROUND_RESULT:
            self._do_round_result()
        elif self.current_state == STATE_GAME_OVER:
            self._do_game_over()
        elif self.current_state == STATE_ALL_CLEAR:
            self._do_all_clear()
        elif self.current_state == STATE_HIGHSCORE_INPUT:
            self._do_highscore_input()
        elif self.current_state == STATE_HIGHSCORE_VIEW:
            self._do_highscore_view()

    # --- 1. 开场动画 ---
    def _do_splash(self):
        # 简单的动画效果
        self.hw.display_text("GIX RHYTHM", scale=2, y_offset=25)
        self.hw.play_tone(523, 0.1) # C5
        time.sleep(0.1)
        self.hw.play_tone(659, 0.1) # E5
        time.sleep(0.1)
        self.hw.play_tone(784, 0.2) # G5
        
        for i in range(settings.NUM_PIXELS):
            self.hw.pixels[i] = (0, 50, 255)
            self.hw.pixels.show()
            time.sleep(0.02)
        
        time.sleep(0.5)
        self.hw.set_leds((0,0,0))
        self.current_state = STATE_MENU_DIFFICULTY

    # --- 2. 难度选择 ---
    def _do_menu_difficulty(self):
        options = settings.DIFFICULTY_NAMES
        self.menu_index = self._handle_menu_input(len(options), self.menu_index)
        
        # 绘制菜单
        layers = [
            {'text': "SELECT DIFFICULTY", 'scale': 1, 'y': 10},
            {'text': f"< {options[self.menu_index]} >", 'scale': 2, 'y': 35}
        ]
        self.hw.display_layers(layers)
        
        if self.hw.is_button_pressed():
            self.difficulty = self.menu_index
            self.hw.play_tone(880, 0.1)
            # 重置游戏全局变量
            self.current_level = 1
            self.total_score = 0
            self.current_state = STATE_GAME_INIT

    # --- 3. 初始化关卡 ---
    def _do_game_init(self):
        level_data = songs.get_level_data(self.current_level)
        self.hw.display_text(f"Level {self.current_level}", scale=2)
        time.sleep(1.0)
        self.hw.display_text(level_data['title'], scale=1)
        time.sleep(1.0)
        
        # 初始化游戏引擎
        self.current_game_engine = RhythmGame(self.hw, level_data, self.difficulty)
        self.current_game_engine.start()
        
        self.current_state = STATE_GAME_PLAYING

    # --- 4. 游戏进行中 ---
    def _do_game_playing(self):
        if self.current_game_engine:
            self.current_game_engine.update()
            
            # 检查是否结束
            if self.current_game_engine.is_won:
                # 记录本关分数
                self.last_level_score = self.current_game_engine.score
                self.total_score += self.last_level_score
                
                # 检查是否通关所有10关
                if self.current_level >= settings.MAX_GAME_LEVELS:
                    self.current_state = STATE_ALL_CLEAR
                else:
                    self.current_state = STATE_ROUND_RESULT
                    
            elif self.current_game_engine.is_game_over:
                # 失败（目前逻辑MISS不导致GameOver，但如果未来修改了可以在这里接）
                self.current_state = STATE_GAME_OVER

    # --- 5. 单关结算菜单 ---
    def _do_round_result(self):
        # 选项: Next Level, Replay Level, Quit
        options = ["NEXT LEVEL", "REPLAY", "QUIT"]
        self.menu_index = self._handle_menu_input(len(options), self.menu_index)
        
        layers = [
            {'text': "LEVEL CLEARED!", 'scale': 1, 'y': 5},
            {'text': f"Score: {self.current_game_engine.score}", 'scale': 1, 'y': 18},
            {'text': f"Total: {self.total_score}", 'scale': 1, 'y': 28},
            {'text': f"> {options[self.menu_index]}", 'scale': 1, 'y': 50}
        ]
        self.hw.display_layers(layers)
        
        if self.hw.is_button_pressed():
            if self.menu_index == 0: # Next
                self.current_level += 1
                self.menu_index = 0
                self.current_state = STATE_GAME_INIT
            elif self.menu_index == 1: # Replay
                # 回滚分数
                self.total_score -= self.last_level_score
                self.current_state = STATE_GAME_INIT
            elif self.menu_index == 2: # Quit
                self.current_state = STATE_HIGHSCORE_INPUT

    # --- 6. 游戏失败 (Game Over) ---
    def _do_game_over(self):
        # 选项: Retry, Quit
        options = ["RETRY LEVEL", "QUIT GAME"]
        self.menu_index = self._handle_menu_input(len(options), self.menu_index)
        
        layers = [
            {'text': "GAME OVER", 'scale': 2, 'y': 15},
            {'text': f"> {options[self.menu_index]}", 'scale': 1, 'y': 45}
        ]
        self.hw.display_layers(layers)
        
        if self.hw.is_button_pressed():
            if self.menu_index == 0: # Retry
                # 这里假设失败时不加分，所以不用回滚
                self.current_state = STATE_GAME_INIT
            else: # Quit
                self.current_state = STATE_HIGHSCORE_INPUT

    # --- 7. 全通关 (Level 10 Finished) ---
    def _do_all_clear(self):
        # 强制保存
        layers = [
            {'text': "YOU WIN!", 'scale': 2, 'y': 15},
            {'text': f"Final: {self.total_score}", 'scale': 1, 'y': 35},
            {'text': "Press Button", 'scale': 1, 'y': 55}
        ]
        self.hw.display_layers(layers)
        if self.hw.is_button_pressed():
            self.current_state = STATE_HIGHSCORE_INPUT

    # --- 8. 输入名字并保存 ---
    def _do_highscore_input(self):
        # 名字输入界面: [A] A A -> A [B] A -> ...
        # self.menu_index 这里用来指示当前正在编辑第几个字母(0-2)
        # 我们需要额外的状态来存储但这只是一个简单的状态机
        
        if not hasattr(self, 'name_chars'):
            self.name_chars = [65, 65, 65] # ASCII 'A'
            self.char_idx = 0
            
        # 读取旋转编码器改变当前字符
        delta = self.hw.get_encoder_delta()
        if delta != 0:
            self.name_chars[self.char_idx] += delta
            # 限制在 A-Z (65-90)
            if self.name_chars[self.char_idx] > 90: self.name_chars[self.char_idx] = 65
            if self.name_chars[self.char_idx] < 65: self.name_chars[self.char_idx] = 90

        # 构建显示字符串
        name_str = "".join([chr(c) for c in self.name_chars])
        
        # 指示器
        pointer_str = "  "
        if self.char_idx == 0: pointer_str = "^    "
        elif self.char_idx == 1: pointer_str = "  ^  "
        elif self.char_idx == 2: pointer_str = "    ^"

        layers = [
            {'text': "ENTER INITIALS", 'scale': 1, 'y': 10},
            {'text': f"Score: {self.total_score}", 'scale': 1, 'y': 20},
            {'text': name_str, 'scale': 2, 'y': 40},
            {'text': pointer_str, 'scale': 1, 'y': 55}
        ]
        self.hw.display_layers(layers)

        if self.hw.is_button_pressed():
            self.char_idx += 1
            if self.char_idx > 2:
                # 输入完成，保存
                final_name = "".join([chr(c) for c in self.name_chars])
                self.hs_manager.add_score(final_name, self.total_score)
                # 清理状态供下次使用
                del self.name_chars 
                self.char_idx = 0
                self.menu_index = 0
                self.current_state = STATE_HIGHSCORE_VIEW

    # --- 9. 查看排行榜 ---
    def _do_highscore_view(self):
        scores = self.hs_manager.get_high_scores()
        
        layers = [{'text': "LEADERBOARD", 'scale': 1, 'y': 5}]
        
        start_y = 18
        for i, entry in enumerate(scores):
            # 只显示前4名因为屏幕太小，或者分屏
            if i >= 4: break 
            row_text = f"{i+1}. {entry['name']}  {entry['score']}"
            layers.append({'text': row_text, 'scale': 1, 'y': start_y + (i * 10), 'x': 10})
        
        layers.append({'text': "Press to Reset", 'scale': 1, 'y': 58})
        
        self.hw.display_layers(layers)
        
        if self.hw.is_button_pressed():
            self.menu_index = 0
            self.current_state = STATE_MENU_DIFFICULTY

    # --- 辅助函数 ---
    def _handle_menu_input(self, num_items, current_idx):
        delta = self.hw.get_encoder_delta()
        if delta != 0:
            new_idx = current_idx + delta
            # 循环菜单
            if new_idx < 0: new_idx = num_items - 1
            if new_idx >= num_items: new_idx = 0
            return new_idx
        return current_idx

# --- Main Entry ---
if __name__ == "__main__":
    app = GameApp()
    app.run()