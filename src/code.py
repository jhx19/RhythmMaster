import time
import board
import microcontroller
import struct
import settings
import songs
from hardware import HardwareManager
from game_engine import RhythmGame

STATE_SPLASH = 0
STATE_MENU_DIFFICULTY = 1
STATE_MENU_LEVEL = 2
STATE_PLAYING = 3
STATE_GAME_OVER = 4
STATE_HIGHSCORE_ENTRY = 5
STATE_HIGHSCORE_VIEW = 6

class HighScoreManager:
    HEADER = b'\xBE\xF1'  
    MAX_ENTRIES = 6
    ENTRY_SIZE = 7 
    OFFSET = 0 

    def __init__(self):
        self.nvm = microcontroller.nvm
        if self.nvm[0:2] != self.HEADER:
            self._reset_nvm()

    def _reset_nvm(self):
        print("Initializing High Scores...")
        self.nvm[0:2] = self.HEADER
        empty_data = (b'GIX', 100)
        for i in range(self.MAX_ENTRIES):
            self._write_entry(i, *empty_data)

    def _write_entry(self, index, name_bytes, score):
        start = 2 + index * self.ENTRY_SIZE
        data = struct.pack('<3sI', name_bytes, score)
        self.nvm[start : start + self.ENTRY_SIZE] = data

    def get_high_scores(self):
        scores = []
        for i in range(self.MAX_ENTRIES):
            start = 2 + i * self.ENTRY_SIZE
            data = self.nvm[start : start + self.ENTRY_SIZE]
            try:
                name, score = struct.unpack('<3sI', data)
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
        
        for i, (n, s) in enumerate(current_scores):
            self._write_entry(i, n.encode('utf-8'), s)

class GameApp:
    def __init__(self):
        self.hw = HardwareManager()
        self.hs_manager = HighScoreManager()
        self.state = STATE_SPLASH
        
        self.difficulty = settings.DIFFICULTY_EASY
        self.current_level_index = 0 
        self.session_score = 0      
        self.current_game_engine = None
        self.last_level_score = 0   
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
            time.sleep(0.01)

    def do_splash(self):
        self.hw.display_layers([
            {'text': "GIX", 'scale': 3, 'y': 20},
            {'text': "RHYTHM", 'scale': 2, 'y': 50}
        ])
        self.hw.play_tone(440, 0.1)
        self.hw.play_tone(554, 0.1)
        self.hw.play_tone(659, 0.2)
        
        for i in range(10):
            color = settings.GRADIENT_BLUE[i % 4]
            self.hw.pixels.fill((0,0,0))
            self.hw.set_pixel_segment(i, i+5, color)
            time.sleep(0.05)
        
        self.hw.set_leds((0,0,0))
        time.sleep(0.5)
        self.state = STATE_MENU_DIFFICULTY

    def _run_menu(self, title, items, start_idx=0):
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

        idx_prev = (selected - 1) % num_items 
        idx_curr = selected
        idx_next = (selected + 1) % num_items
        
        text_prev = items[idx_prev]
        text_curr = f"> {items[idx_curr]} <" 
        text_next = items[idx_next]
        
        # Title: y=5 
        # Prev:  y=20 
        # Curr:  y=35 
        # Next:  y=50
        
        layers = [
            {'text': title, 'scale': 1, 'y': 5},
            
            {'text': text_prev, 'scale': 1, 'y': 20},
            
            {'text': text_curr, 'scale': 1, 'y': 35},
            
            {'text': text_next, 'scale': 1, 'y': 50}
        ]
        
        self.hw.display_layers(layers)

    def do_menu_difficulty(self):
        self.session_score = 0
        
        options = ["EASY", "NORMAL", "HARD", "High Scores"]
        idx = self._run_menu("SELECT DIFFICULTY", options)
        
        if idx == 3:
            self.state = STATE_HIGHSCORE_VIEW
        else:
            self.difficulty = idx 
            self.state = STATE_MENU_LEVEL

    def do_menu_level(self):
        total_songs = len(songs.SONG_LIBRARY)
        options = [f"Level {i+1}" for i in range(total_songs)]
        options.append("Back")
        
        idx = self._run_menu("SELECT LEVEL", options)
        
        if idx == len(options) - 1:
            self.state = STATE_MENU_DIFFICULTY
        else:
            self.current_level_index = idx
            self.state = STATE_PLAYING

    def do_playing(self):
        level_data = songs.get_level_data(self.current_level_index + 1)
        if not level_data:
            print("Error: No level data")
            self.state = STATE_MENU_DIFFICULTY
            return

        self.current_game_engine = RhythmGame(self.hw, level_data, self.difficulty)
        
        for i in range(3, 0, -1):
            self.hw.display_layers([
                {'text': f"Level {self.current_level_index + 1}", 'scale': 1, 'y': 10},
                {'text': str(i), 'scale': 4, 'y': 40}
            ])
            self.hw.play_tone(440, 0.1)
            time.sleep(0.8)
        
        self.current_game_engine.start()
        
        while True:
            self.current_game_engine.update()
            
            if self.current_game_engine.is_game_over:
                self.hw.play_tone(100, 0.5)
                self.state = STATE_GAME_OVER
                break
                
            if self.current_game_engine.is_won:
                self.hw.play_tone(1000, 0.2)
                time.sleep(0.1)
                self.hw.play_tone(1200, 0.4)
                self.state = STATE_GAME_OVER
                break
                
    def do_game_over(self):
        engine = self.current_game_engine
        is_win = engine.is_won
        self.last_level_score = int(engine.score)
        total_now = self.session_score + self.last_level_score
        
        title = "CLEARED!" if is_win else "GAME OVER"
        self.hw.display_layers([
            {'text': title, 'scale': 2, 'y': 10},
            {'text': f"Score: {self.last_level_score}", 'scale': 1, 'y': 30},
            {'text': f"Total: {total_now}", 'scale': 1, 'y': 45},
            {'text': f"Max Combo: {engine.combo}", 'scale': 1, 'y': 60}
        ])
        
        time.sleep(1.0) 
        while not self.hw.is_button_pressed():
            time.sleep(0.1)
            
        menu_options = ["Retry Level", "Save & Quit"]
        
        can_next = is_win and (self.current_level_index < settings.MAX_GAME_LEVELS - 1)
        if can_next:
            menu_options.insert(1, "Next Level")
        
        idx = self._run_menu("RESULT MENU", menu_options)
        
        choice = menu_options[idx]
        
        if choice == "Retry Level":
            self.state = STATE_PLAYING
            
        elif choice == "Next Level":
            self.session_score += self.last_level_score
            self.current_level_index += 1
            self.state = STATE_PLAYING
            
        elif choice == "Save & Quit":
            self.session_score += self.last_level_score
            self.state = STATE_HIGHSCORE_ENTRY

    def do_highscore_entry(self):
        final_score = self.session_score
        initials = [65, 65, 65] # ASCII 'A', 'A', 'A'
        cursor = 0
        
        need_refresh = True
        
        while cursor < 3:
            if need_refresh:
                char_str = "".join([chr(c) for c in initials])
                indicator = " " * cursor + "^" + " " * (2-cursor)
                
                self.hw.display_layers([
                    {'text': "NEW RECORD!", 'scale': 1, 'y': 10},
                    {'text': f"Score: {final_score}", 'scale': 1, 'y': 25},
                    {'text': char_str, 'scale': 3, 'y': 45},
                    {'text': indicator, 'scale': 2, 'y': 60} 
                ])
                need_refresh = False 

            delta = self.hw.get_encoder_delta()
            if delta != 0:
                initials[cursor] += delta
                if initials[cursor] > 90: initials[cursor] = 65
                if initials[cursor] < 65: initials[cursor] = 90
                need_refresh = True 
            
            if self.hw.is_button_pressed():
                self.hw.play_tone(1760, 0.1)
                cursor += 1
                need_refresh = True 
                time.sleep(0.2) 

            time.sleep(0.05)
            
        name = "".join([chr(c) for c in initials])
        self.hs_manager.add_score(name, final_score)
        
        self.hw.display_layers([
            {'text': "SAVED!", 'scale': 3, 'y': 32}
        ])
        time.sleep(1.5)
        self.state = STATE_HIGHSCORE_VIEW

    def do_highscore_view(self):
        scores = self.hs_manager.get_high_scores()
        
        items = []
        for i, (name, s) in enumerate(scores):
            items.append(f"{i+1}. {name}  {s}")
            
        items.append("[ Back ]")
        
        self._run_menu("HIGH SCORES", items)
        
        self.state = STATE_MENU_DIFFICULTY

if __name__ == "__main__":
    game = GameApp()
    game.run()

