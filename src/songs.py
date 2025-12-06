import settings

# --- 1. 音符频率表 (Hz) ---
# 来自 buzzer_test.py
NOTES = {
    'C4': 262, 'D4': 294, 'E4': 330, 'F4': 349, 'G4': 392, 
    'A4': 440, 'B4': 494, 'C5': 523, 
    'REST': 0
}

# --- 2. 基础节拍定义 (秒) ---
# 可以根据游戏难度系数调整这些值
QN = 0.4  # Quarter Note (四分音符) - 标准动作时间
HN = 0.8  # Half Note (二分音符) - 长动作或休息

# --- 3. 乐曲库 ---
# 结构说明：
# 每个关卡是一个字典，包含：
# - 'title': 显示在屏幕上的名字
# - 'steps': 一个列表，每个元素是元组 (音符名, 持续时间, 目标动作)
#   如果 target_move 是 settings.MOVE_NONE，则表示这段音乐是纯播放，不需要玩家操作(休息)

SONG_LIBRARY = [
    # --- Level 1: Twinkle Twinkle Little Star ---
    {
        "title": "Twinkle Star",
        "steps": [
            # 歌词: Twin-kle Twin-kle Lit-tle Star (1 1 5 5 6 6 5)
            # 设计逻辑: 
            # C4 (Do) -> Touch 1 (最左)
            # G4 (Sol)-> Touch 2 (中间)
            # A4 (La) -> Touch 3 (右边)
            # 结尾 G4 -> Shake (摇晃，模拟高潮)

            ('C4', QN, settings.MOVE_TOUCH_1),
            ('C4', QN, settings.MOVE_NONE),
            ('G4', QN, settings.MOVE_TOUCH_2),
            ('G4', QN, settings.MOVE_NONE),
            ('A4', QN, settings.MOVE_TOUCH_3),
            ('A4', QN, settings.MOVE_NONE),
            ('G4', HN, settings.MOVE_RIGHT), # 长音用 Double Tap 增加变化

            # 歌词: How I won-der what you are (4 4 3 3 2 2 1)
            # F4 (Fa) -> Touch 4 (D3键)
            # E4 (Mi) -> Touch 3
            # D4 (Re) -> Touch 2
            # C4 (Do) -> Touch 1
            
            ('F4', QN, settings.MOVE_TOUCH_4),
            ('F4', QN, settings.MOVE_NONE),
            ('E4', QN, settings.MOVE_TOUCH_3),
            ('E4', QN, settings.MOVE_NONE),
            ('D4', QN, settings.MOVE_TOUCH_2),
            ('D4', QN, settings.MOVE_NONE),
            ('C4', HN, settings.MOVE_LEFT), # 结尾用 Tilt Left
        ]
    },

    # --- Level 2: (预留位置，未来可以复制上面的结构添加) ---
    # {
    #     "title": "Mario Theme",
    #     "steps": [ ... ]
    # }
]

def get_level_data(level_index):
    """
    安全地获取关卡数据。
    如果索引超出范围，则循环回到第一个关卡（或处理为随机）。
    """
    total_songs = len(SONG_LIBRARY)
    if total_songs == 0:
        return None
    
    # 取模运算，确保 Level 11 会回到 Level 1 的音乐，防止报错
    safe_index = (level_index - 1) % total_songs 
    return SONG_LIBRARY[safe_index]

def get_frequency(note_name):
    """辅助函数：根据名字查频率"""
    return NOTES.get(note_name, 0)