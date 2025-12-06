import time
import board
import neopixel

# --- 配置部分 ---
PIXEL_PIN = board.D4        # 连接 NeoPixel 数据线的 ESP32 引脚
NUM_PIXELS = 28             # 灯带上 LED 的总数量
LEDS_PER_SEGMENT = 7        # 每段（行）的 LED 数量
BRIGHTNESS = 0.5            # 亮度 (0.0 到 1.0)
COLOR = (0, 0, 255)         # 闪烁的颜色 (R, G, B) - 蓝色
DELAY_TIME = 0.05           # 每个 LED 亮起的延迟时间 (秒)
COOLDOWN_TIME = 0.3         # 完成一次循环后的暂停时间 (秒)

# 初始化 NeoPixel 对象
pixels = neopixel.NeoPixel(
    PIXEL_PIN, 
    NUM_PIXELS, 
    brightness=BRIGHTNESS, 
    auto_write=False
)

print("✅ NeoPixel 初始化成功。开始蛇形闪烁效果...")

# --- 辅助函数：清除灯带 ---
def clear_pixels():
    """将所有 LED 颜色设置为黑色 (关闭) 并立即更新。"""
    pixels.fill((0, 0, 0))
    pixels.show()

# --- 核心闪烁函数 ---

def flash_segment(start_index, end_index, direction, color):
    """
    控制一个分段的 LED 依次点亮。
    
    start_index: 逻辑上的起始编号（例如，第1行是 0）
    end_index: 逻辑上的结束编号（例如，第1行是 6）
    direction: 闪烁的方向 (+1 表示正向，-1 表示反向)
    """
    
    # Python 的 range(start, stop, step) 函数：
    # range(start_index, end_index + direction, direction)
    # 如果 direction 是 +1 (正向)，end 应该是 end_index + 1
    # 如果 direction 是 -1 (反向)，end 应该是 end_index - 1
    
    # 调整 range 的结束点以确保包含 end_index
    stop_index = end_index + direction
    
    for i in range(start_index, stop_index, direction):
        # 清除所有灯光，只点亮当前灯
        clear_pixels() 
        pixels[i] = color
        pixels.show()
        time.sleep(DELAY_TIME)
        
    # 循环结束后，清空灯带
    clear_pixels()
    time.sleep(COOLDOWN_TIME)


# --- 主循环 ---
while True:
    # 1. 第一行: 0 到 6 (正向)
    print("▶️ 闪烁第 1 行 (0 -> 6)")
    flash_segment(
        start_index=0, 
        end_index=6, 
        direction=1, 
        color=COLOR
    )

    # 2. 第二行: 13 到 7 (反向)
    print("◀️ 闪烁第 2 行 (13 -> 7)")
    flash_segment(
        start_index=13, 
        end_index=7, 
        direction=-1, 
        color=COLOR
    )
    
    # 3. 第三行: 14 到 20 (正向)
    print("▶️ 闪烁第 3 行 (14 -> 20)")
    flash_segment(
        start_index=14, 
        end_index=20, 
        direction=1, 
        color=COLOR
    )

    # 4. 第四行: 27 到 21 (反向)
    print("◀️ 闪烁第 4 行 (27 -> 21)")
    flash_segment(
        start_index=27, 
        end_index=21, 
        direction=-1, 
        color=COLOR
    )
