import microcontroller
import struct

# NVM 内存布局:
# 我们需要保存前6名。
# 每个条目包含: 3个字节(姓名字符) + 4个字节(分数, unsigned int) = 7字节
# 总共 6 * 7 = 42 字节
ENTRY_SIZE = 7
MAX_ENTRIES = 6
TOTAL_SIZE = ENTRY_SIZE * MAX_ENTRIES

class HighScoreManager:
    def __init__(self):
        self.nvm = microcontroller.nvm
        # 如果NVM是空的或者全是0xFF(出厂状态)，初始化它
        if self.nvm[0:TOTAL_SIZE] == b'\xff' * TOTAL_SIZE:
            self._reset_nvm()

    def _reset_nvm(self):
        """初始化排行榜为默认值"""
        empty_data = bytearray()
        for _ in range(MAX_ENTRIES):
            empty_data.extend(b'AAA') # 默认名字
            empty_data.extend(struct.pack('>I', 0)) # 默认分数 0
        self.nvm[0:TOTAL_SIZE] = empty_data

    def get_high_scores(self):
        """读取所有高分记录，返回列表 [{'name': 'ABC', 'score': 123}, ...]"""
        scores = []
        try:
            for i in range(MAX_ENTRIES):
                offset = i * ENTRY_SIZE
                name_bytes = self.nvm[offset : offset+3]
                score_bytes = self.nvm[offset+3 : offset+7]
                
                name = "".join([chr(b) for b in name_bytes])
                score = struct.unpack('>I', score_bytes)[0]
                scores.append({'name': name, 'score': score})
        except Exception as e:
            print(f"NVM Read Error: {e}")
            self._reset_nvm()
            return self.get_high_scores()
            
        # 再次排序确保顺序正确
        scores.sort(key=lambda x: x['score'], reverse=True)
        return scores

    def add_score(self, name, score):
        """尝试添加新分数。如果够高则插入，并保存到NVM"""
        current_scores = self.get_high_scores()
        current_scores.append({'name': name, 'score': score})
        # 排序并取前6名
        current_scores.sort(key=lambda x: x['score'], reverse=True)
        current_scores = current_scores[:MAX_ENTRIES]
        
        # 写入 NVM
        data_buffer = bytearray()
        for entry in current_scores:
            # 确保名字是3个字符的大写
            n_str = entry['name'][:3].upper().ljust(3, 'A')
            data_buffer.extend(n_str.encode('utf-8'))
            data_buffer.extend(struct.pack('>I', entry['score']))
            
        self.nvm[0:TOTAL_SIZE] = data_buffer
        print("Score saved to NVM.")