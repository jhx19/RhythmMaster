import settings

# --- 1. 音符频率表 (Hz) ---
NOTES = {
    'REST': 0,
    'G3': 196, 'Ab3': 207, 'A3': 220, 'Bb3': 233, 'B3': 247,
    'C4': 262, 'C#4': 277, 'D4': 294, 'Eb4': 311, 'E4': 330, 'F4': 349, 'F#4': 370, 'G4': 392, 'Ab4': 415, 'A4': 440, 'Bb4': 466, 'B4': 494,
    'C5': 523, 'C#5': 554, 'D5': 587, 'Eb5': 622, 'E5': 659, 'F5': 698, 'F#5': 740, 'G5': 784,
}

# --- 2. 基础节拍定义 ---
QN = settings.QN  # Quarter Note (标准拍)
HN = settings.HN  # Half Note (两拍)
EN = QN / 2       # Eighth Note (半拍)
WN = QN * 4       # Whole Note (全音符/长音)

# 动作缩写 (减少代码量)
M_NONE = settings.MOVE_NONE
M_T1 = settings.MOVE_TOUCH_1
M_T2 = settings.MOVE_TOUCH_2
M_T3 = settings.MOVE_TOUCH_3
M_T4 = settings.MOVE_TOUCH_4
M_L  = settings.MOVE_LEFT
M_R  = settings.MOVE_RIGHT
M_TAP = settings.MOVE_TAP

# --- 3. 乐曲库 ---
SONG_LIBRARY = [
    # --- Level 1: Twinkle Twinkle Little Star (完整版) ---
    # 结构: A - B - B - A
    {
        "title": "Twinkle Star",
        "steps": [
            # Section A: Main Theme
            ('C4', QN, M_T1), ('C4', QN, M_T1), ('G4', QN, M_T2), ('G4', QN, M_T2),
            ('A4', QN, M_T3), ('A4', QN, M_T3), ('G4', HN, M_R),
            ('F4', QN, M_T4), ('F4', QN, M_T4), ('E4', QN, M_T3), ('E4', QN, M_T3),
            ('D4', QN, M_T2), ('D4', QN, M_T2), ('C4', HN, M_L),
            
            # Section B: Bridge (重复两次)
            ('G4', QN, M_T2), ('G4', QN, M_T2), ('F4', QN, M_T4), ('F4', QN, M_T4),
            ('E4', QN, M_T3), ('E4', QN, M_T3), ('D4', HN, M_TAP),
            ('G4', QN, M_T2), ('G4', QN, M_T2), ('F4', QN, M_T4), ('F4', QN, M_T4),
            ('E4', QN, M_T3), ('E4', QN, M_T3), ('D4', HN, M_TAP)
        ]
    },

    # --- Level 2: Happy Birthday (完整版) ---
    # 包含高潮部分的跨度跳跃
    {
        "title": "Happy B-Day",
        "steps": [
            # Line 1
            ('C4', EN, M_T1), ('C4', EN, M_NONE), ('D4', QN, M_T2), ('C4', QN, M_T1), ('F4', QN, M_T4), ('E4', HN, M_T3),
            # Line 2
            ('C4', EN, M_T1), ('C4', EN, M_NONE), ('D4', QN, M_T2), ('C4', QN, M_T1), ('G4', QN, M_R),  ('F4', HN, M_T4),
            # Line 3 (High part)
            ('C4', EN, M_T1), ('C4', EN, M_NONE), ('C5', QN, M_TAP),('A4', QN, M_T3), ('F4', QN, M_T4), ('E4', QN, M_T3), ('D4', QN, M_T2),
            # Line 4 (End)
            ('Bb4', EN, M_L), ('Bb4', EN, M_NONE),('A4', QN, M_T3), ('F4', QN, M_T4), ('G4', QN, M_R),  ('F4', HN, M_T4),
        ]
    },

    # --- Level 3: Jingle Bells (Verse + Chorus) ---
    # 增加了前面的主歌部分，然后接副歌
    {
        "title": "Jingle Bells",
        "steps": [            
            # Chorus: "Jingle Bells..."
            ('E4', QN, M_T3), ('E4', QN, M_T3), ('E4', HN, M_TAP),
            ('E4', QN, M_T3), ('E4', QN, M_T3), ('E4', HN, M_TAP),
            ('E4', QN, M_T3), ('G4', QN, M_R),  ('C4', QN, M_T1), ('D4', QN, M_T2), ('E4', HN, M_T3),
            
            # "Oh what fun..."
            ('F4', QN, M_T4), ('F4', QN, M_T4), ('F4', QN, M_T4), ('F4', EN, M_NONE),
            ('F4', QN, M_T4), ('E4', QN, M_T3), ('E4', QN, M_T3), ('E4', EN, M_NONE),
            ('E4', QN, M_T3), ('D4', QN, M_T2), ('D4', QN, M_T2), ('E4', QN, M_T3), ('D4', HN, M_T2), ('G4', HN, M_TAP)
        ]
    },

    # --- Level 4: Mario Theme (Main Loop) ---
    # 经典的切分节奏，增加了长度
    {
        "title": "Mario Bros",
        "steps": [            
            # Main Theme Part A
            ('C4', QN, M_T1), ('REST', EN, M_NONE), ('G3', EN, M_L), ('REST', EN, M_NONE), ('E3', EN, M_NONE),
            ('A3', QN, M_T1), ('B3', QN, M_T2), ('Bb3', EN, M_L), ('A3', QN, M_T1),
            ('G3', EN, M_L), ('E4', QN, M_T3), ('G4', QN, M_R),
            ('A4', QN, M_T4), ('F4', EN, M_T4), ('G4', EN, M_R),
            ('REST', EN, M_NONE), ('E4', QN, M_T3), ('C4', EN, M_T1), ('D4', EN, M_T2), ('B3', EN, M_T1),
            
            # Repeat ending
            ('REST', EN, M_NONE), ('C4', HN, M_TAP),
        ]
    },

    # --- Level 5: Ode to Joy (A-A-B-A Form) ---
    # 完整的欢乐颂结构
    {
        "title": "Ode to Joy",
        "steps": [
            # A Section
            ('E4', QN, M_T3), ('E4', QN, M_T3), ('F4', QN, M_T4), ('G4', QN, M_R),
            ('G4', QN, M_R),  ('F4', QN, M_T4), ('E4', QN, M_T3), ('D4', QN, M_T2),
            ('C4', QN, M_T1), ('C4', QN, M_T1), ('D4', QN, M_T2), ('E4', QN, M_T3),
            ('E4', QN, M_T3), ('D4', EN, M_T2), ('D4', HN, M_T2),
            
            # A Section (Variation End)
            ('E4', QN, M_T3), ('E4', QN, M_T3), ('F4', QN, M_T4), ('G4', QN, M_R),
            ('G4', QN, M_R),  ('F4', QN, M_T4), ('E4', QN, M_T3), ('D4', QN, M_T2),
            ('C4', QN, M_T1), ('C4', QN, M_T1), ('D4', QN, M_T2), ('E4', QN, M_T3),
            ('D4', QN, M_T2), ('C4', EN, M_T1), ('C4', HN, M_TAP),
        ]
    },

    # --- Level 6: Imperial March (Extended) ---
    # 增加第二段高音部分
    {
        "title": "Darth Vader",
        "steps": [
            # Main Motif
            ('G4', QN, M_T2), ('G4', QN, M_T2), ('G4', QN, M_T2),
            ('Eb4', EN, M_T1), ('Bb4', EN, M_T4), ('G4', QN, M_T2),
            ('Eb4', EN, M_T1), ('Bb4', EN, M_T4), ('G4', HN, M_TAP),
            
            # High Motif
            ('D5', QN, M_R), ('D5', QN, M_R), ('D5', QN, M_R),
            ('Eb5', EN, M_T4), ('Bb4', EN, M_T3), ('Gb4', QN, M_T2), # Gb = F#
            ('Eb4', EN, M_T1), ('Bb4', EN, M_T4), ('G4', HN, M_TAP),
        ]
    },

    # --- Level 7: Tetris Theme (A + B Section) ---
    # 俄罗斯方块经典两段式
    {
        "title": "Tetris",
        "steps": [
            # Part A
            ('E4', QN, M_T3), ('B3', EN, M_T1), ('C4', EN, M_T2), ('D4', QN, M_T3), ('C4', EN, M_T2), ('B3', EN, M_T1),
            ('A3', QN, M_L),  ('A3', EN, M_NONE), ('C4', EN, M_T2), ('E4', QN, M_T3), ('D4', EN, M_T2), ('C4', EN, M_T1),
            ('B3', QN, M_T1), ('B3', EN, M_NONE), ('C4', EN, M_T2), ('D4', QN, M_T3), ('E4', QN, M_R),
            ('C4', QN, M_T1), ('A3', QN, M_L), ('A3', QN, M_L),
        ]
    },

    # --- Level 8: Zelda's Lullaby (Extended) ---
    # 舒缓的长音
    {
        "title": "Zelda Song",
        "steps": [
            ('B3', HN, M_T1), ('D4', QN, M_T2), ('A3', HN, M_L),  ('REST', QN, M_NONE),
            ('B3', HN, M_T1), ('D4', QN, M_T2), ('A3', HN, M_L),  ('REST', QN, M_NONE),
            ('B3', HN, M_T1), ('D4', QN, M_T2), ('A4', HN, M_T3), ('G4', QN, M_T2),
            ('D4', HN, M_T2), ('C4', EN, M_T1), ('B3', EN, M_L),  ('A3', HN, M_L),
            ('REST', QN, M_NONE),
            ('B3', HN, M_T1), ('D4', QN, M_T2), ('A4', HN, M_R),  ('G4', QN, M_T2),
            ('D5', HN, M_TAP),
        ]
    },

    # --- Level 9: Mission Impossible (Loop x4) ---
    # 5/4拍 循环洗脑
    {
        "title": "Impossible",
        "steps": [
            # Loop 1
            ('G4', QN, M_T2), ('G4', QN, M_T2), ('NONE', EN, M_NONE), 
            ('Bb4', EN, M_T4), ('C5', EN, M_R),
            ('G4', QN, M_T2), ('G4', QN, M_T2),
            ('F4', EN, M_T1), ('F#4', EN, M_T2),
            
            # Loop 3 (High Note)
            ('G4', QN, M_T2), ('G4', QN, M_T2), ('NONE', EN, M_NONE),
            ('Bb4', EN, M_T4), ('C5', EN, M_R),
            ('G4', QN, M_T2), ('G4', QN, M_T2),
            ('E4', EN, M_T3), ('Eb4', EN, M_T3), ('D4', HN, M_TAP),
        ]
    },

    # --- Level 10: The Final Boss (Endurance Run) ---
    # 极长且复杂的音阶练习
    {
        "title": "BOSS FIGHT",
        "steps": [
            # Phase 1: Ascending Scale
            ('C4', EN, M_T1), ('D4', EN, M_T2), ('E4', EN, M_T3), ('F4', EN, M_T4),
            ('G4', EN, M_T1), ('A4', EN, M_T2), ('B4', EN, M_T3), ('C5', EN, M_R),
            
            # Phase 2: Descending Scale
            ('C5', EN, M_R), ('B4', EN, M_L), ('A4', EN, M_R), ('G4', EN, M_L),
            ('F4', EN, M_T4), ('E4', EN, M_T3), ('D4', EN, M_T2), ('C4', EN, M_T1),
            
            # Phase 3: Arpeggios (C Major)
            ('C4', EN, M_T1), ('E4', EN, M_T3), ('G4', EN, M_R), ('C5', EN, M_TAP),
            ('G4', EN, M_R), ('E4', EN, M_T3), ('C4', EN, M_T1), ('REST', EN, M_NONE),
            
            # Phase 4: Arpeggios (G Major)
            ('G3', EN, M_L), ('B3', EN, M_T1), ('D4', EN, M_T2), ('G4', EN, M_TAP),
            ('D4', EN, M_T2), ('B3', EN, M_T1), ('G3', EN, M_L), ('REST', EN, M_NONE),

            # Phase 5: Chaos (Fast Random)
            ('C4', EN, M_T1), ('C5', EN, M_R), ('G4', EN, M_T2), ('E4', EN, M_T3),
            ('A4', EN, M_T3), ('F4', EN, M_T4), ('D4', EN, M_T2), ('B3', EN, M_L),
            
            # Final Hit
            ('C4', HN, M_TAP), ('G4', HN, M_TAP), ('C5', WN, M_TAP),
        ]
    },
]

def get_level_data(level_index):
    total_songs = len(SONG_LIBRARY)
    if total_songs == 0:
        return None
    safe_index = (level_index - 1) % total_songs 
    return SONG_LIBRARY[safe_index]

def get_frequency(note_name):
    return NOTES.get(note_name, 0)