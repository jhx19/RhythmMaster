
# Rhythm Master

**Rhythm Master** is an embedded, 90s-style handheld electronic rhythm game powered by the Seeed Studio XIAO ESP32C3. Inspired by classic rhythm games like *Rhythm Master* and *Guitar Hero*, this device combines physical touch inputs with motion-sensing controls to create an immersive musical gaming experience.

Players must hit notes in sync with the music using a 4-key capacitive touch keypad and a motion-sensing "joystick." The game features multiple songs, difficulty settings, high score tracking, and real-time visual feedback via NeoPixel LED strips and an OLED display.


## Game Overview

The goal of ** Rhythm Master** is to hit falling notes accurately as they reach the bottom of the track. The game evaluates your timing and accuracy, awarding points for "Perfect" and "Good" hits while penalizing "Misses."

### Key Features

  * **3 Difficulty Settings:** Easy, Normal, and Hard (Adjusts note speed and timing windows).
  * **10 Levels:** Progress through varying songs including *Twinkle Star*, *Mario Theme*, *Tetris*, and *Star Wars*.
  * **High Score System:** Saves top scores to the ESP32's non-volatile memory (NVM).
  * **Combo System:** consecutive hits build up a combo counter for bonus points.
  * **Rich Feedback:** Real-time audio synthesis and dynamic LED lighting effects.

## How to Play

### Controls

The game utilizes a hybrid control scheme designed for two-handed play:

1.  **Right Hand (Notes):** Four capacitive touch keys (Copper Foil) correspond to the four falling note tracks. Tap the corresponding key when the light reaches the bottom.
2.  **Left Hand (Motion/Tilt):** A physical "joystick" embedded with an accelerometer (ADXL345).
      * **Tilt Left/Right:** Tilt the controller to hit special directional notes (indicated by Blue gradient lights).
      * **Double Tap:** Tap the body of the joystick firmly for special "Beat" notes (indicated by Red lights).
3.  **Menu Navigation:** Use the Rotary Encoder to scroll through menus and press the knob to select.

### Visual Indicators

  * **OLED Screen:** Displays current Score, Hit Feedback (PERFECT/GOOD/MISS), and Combo count.
  * **NeoPixel LEDs:** Represents the 4 music tracks.
      * **Green:** Standard Touch Notes.
      * **Blue Gradient:** Tilt Notes (Darker blue for one direction, lighter for the other).
      * **Pink:** Double Tap Notes.

### Scoring

  * **Perfect:** +20 points (High precision).
  * **Good:** +10 points (Standard hit).
  * **Combo Bonus:** +5 extra points per hit after a combo of 2.
  * **Miss:** 0 points (Combo reset).

## Hardware & Components

The system is built around the **Seeed Studio XIAO ESP32C3** using CircuitPython.

| Component | Pin / Connection | Description |
| :--- | :--- | :--- |
| **MCU** | N/A | Seeed Studio XIAO ESP32C3 |
| **Touch Inputs** | D0, D1, D2, D3 | 4x Copper Foil pads using `touchio` for track inputs. |
| **Motion Sensor** | I2C (D6 SDA, D7 SCL) | **ADXL345 Accelerometer**. Detects X-axis Tilt and Double Tap events. |
| **Display** | I2C (D6 SDA, D7 SCL) | **SSD1306 OLED (128x64)**. Shows GUI and game status. |
| **Visuals** | D4 | **WS2812B NeoPixel Strip (28 LEDs)**. Arranged in a "snake" pattern (4 rows of 7 LEDs). |
| **Audio** | D5 | **Passive Buzzer**. Generates PWM tones for music. |
| **Controls** | D8, D9, D10 | **Rotary Encoder**. Used for menu selection and settings. |
| **Power** | Battery Input | LiPo Battery with an On/Off toggle switch. |

### Implementation Details

  * **Snake Mapping:** The single LED strip is logically mapped into 4 separate tracks using a software look-up table (`hardware.py`), allowing a continuous strip to function as a 4-lane display.
  * **Non-Blocking Audio:** A custom audio engine (`game_engine.py`) synthesizes music in real-time using `pwmio` without pausing the game loop, ensuring smooth animation and input detection.
  * **Calibration:** On startup, the system automatically calibrates the ADXL345 baseline and capacitive touch thresholds to adapt to the environment.

## Enclosure Design


The enclosure is designed to mimic the ergonomics of a classic arcade console or handheld rhythm game, specifically optimized for the dual-hand control scheme.

1.  **Ergonomics:**

      * **Left-Hand Joystick:** I designed a custom 3D-printed handle structure that mimics a car gear stick. The ADXL345 sensor is embedded inside this handle. This allows the player to intuitively "steer" the music by tilting their left hand, translating physical motion into game inputs.
      * **Right-Hand Piano Layout:** The right side features a flat surface with four conductive zones. These allow the player to use four fingers independently to tap notes, simulating the feeling of playing a piano or the classic *Rhythm Master* phone interface.

2.  **Material Choices:**

      * **Copper Foil:** Chosen for the touch keys because it is highly conductive, thin, and can be easily cut into ergonomic shapes and covered with a sticker for a smooth texture similar to a smartphone screen.
      * **Wooden Base Laser-Cut:** The main body is constructed from laser-cut plywood, providing a sturdy yet lightweight frame. The wood gives a retro aesthetic while being easy to work with for mounting components.
3.  **Visual Layout:**

      * The OLED screen and NeoPixel strips are centered to keep the player's focus in one area. The LED strips are aligned directly above the touch pads to provide a clear visual connection between the falling note and the input zone.

## Software Architecture

The code is written in **CircuitPython** and organized into modular classes:

  * `code.py`: The main entry point. Manages the **State Machine** (Splash -\> Menu -\> Playing -\> GameOver -\> HighScore).
  * `game_engine.py`: Handles the core gameplay loop, hit detection logic (windows for Perfect/Good), score calculation, and LED rendering.
  * `hardware.py`: A hardware abstraction layer that manages sensors, display drivers, and input filtering (debouncing/smoothing).
  * `songs.py`: Contains the musical data (notes and timing) for all 10 levels.
  * `settings.py`: Central configuration file for pins, colors, and difficulty constants.

## Diagrams



  * **System Block Diagram:** Shows the data flow between the ESP32, Sensors, and Outputs.
  * **Circuit Diagram:** Detailed wiring schematic for the perfboard assembly.

