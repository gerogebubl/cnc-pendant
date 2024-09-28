# Import statements
from micropython import const
import lcd_bus
import machine
import time
import json
import gc9a01
import lvgl as lv
import _thread
import i2c
import ft6x36
import task_handler

# Constants
_WIDTH = const(240)
_HEIGHT = const(240)
_DC_PIN = const(4)
_MOSI_PIN = const(5)
_MISO_PIN = const(16)
_SCLK_PIN = const(6)
_CS_PIN = const(7)
_FREQ = const(60000000)
_RESET_PIN = const(8)
_POWER_PIN = None
_BACKLIGHT_PIN = const(9)
_OFFSET_X = const(0)
_OFFSET_Y = const(0)
ENCODER_CLK_PIN = const(40)
ENCODER_DT_PIN = const(41)

# Global variables
current_state = 0
states = ['X', 'Y', 'Z', 'F', 'S']
active_button = 0
feed = 100
step = 1
force_update = False

last_encoded = 0
encoder_value = 0
last_update_time = 0
DEBOUNCE_TIME = 1  # milliseconds
encoder_steps = 0  # New variable to track steps within a detent

prev_execution_time = 0
INTERVAL = 5000

# Hardware setup
spi_bus = machine.SPI.Bus(host=1, sck=_SCLK_PIN, mosi=_MOSI_PIN, miso=_MISO_PIN)
display_bus = lcd_bus.SPIBus(spi_bus=spi_bus, dc=_DC_PIN, freq=_FREQ, cs=_CS_PIN, dc_low_on_data=False, cs_high_active=False)
display = gc9a01.GC9A01(
    data_bus=display_bus,
    display_width=_WIDTH,
    display_height=_HEIGHT,
    frame_buffer1=None,
    frame_buffer2=None,
    reset_pin=_RESET_PIN,
    reset_state=gc9a01.STATE_LOW,
    power_pin=_POWER_PIN,
    power_on_state=gc9a01.STATE_HIGH,
    backlight_pin=_BACKLIGHT_PIN,
    backlight_on_state=gc9a01.STATE_HIGH,
    offset_x=_OFFSET_X,
    offset_y=_OFFSET_Y,
    color_space=lv.COLOR_FORMAT.RGB565,
    rgb565_byte_swap=True
)
display.set_power(True)
display.init()
display.set_backlight(100)

i2c_bus = i2c.I2C.Bus(host=1, scl=12, sda=11)
touch_i2c = i2c.I2C.Device(i2c_bus, dev_id=ft6x36.I2C_ADDR, reg_bits=ft6x36.BITS)
indev = ft6x36.FT6x36(touch_i2c)

# Rotary Encoder setup
encoder_clk = machine.Pin(ENCODER_CLK_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
encoder_dt = machine.Pin(ENCODER_DT_PIN, machine.Pin.IN, machine.Pin.PULL_UP)

last_clk_state = encoder_clk.value()

# Function definitions
def update_value(value, is_increasing, min_value, max_value):
    if is_increasing:
        if value > 1000:
            new_value = value + 2500
        elif value == 1000:
            new_value = 2500
        elif value > 100:
            new_value = value + 250
        elif value == 100:
            new_value = 250
        elif value > 10:
            new_value = value + 25
        elif value == 10:
            new_value = 25
        elif value > 1:
            new_value = value + 2.5
        elif value == 1:
            new_value = 2.5
        elif value >= 0.25:
            new_value = round(value + 0.25, 2)
        elif value >= 0.1:
            new_value = 0.25
        elif value >= 0:
            new_value = round(value + 0.01, 2)
        else:
            new_value = value
    else:
        if value >= 5000:
            new_value = value - 2500
        elif value == 2500:
            new_value = 1000
        elif value > 250:
            new_value = value - 250
        elif value == 250:
            new_value = 100
        elif value > 10:
            new_value = value - 25
        elif value >= 5:
            new_value = value - 2.5
        elif value == 2.5:
            new_value = 1
        elif value >= 0.5:
            new_value = round(value - 0.25, 2)
        elif value == 0.25:
            new_value = 0.1
        elif value > 0:
            new_value = max(0, value - 0.01)
        else:
            new_value = value

    return max(min_value, min(new_value, max_value))

class QueryError(Exception):
    pass

def query_object_model(uart_id, baud_rate, tx_pin, rx_pin, object_model=None):
    try:
        uart = machine.UART(uart_id, baudrate=baud_rate, tx=tx_pin, rx=rx_pin)

        if object_model in ["move", "move_wcs"]:
            command = 'M409 K"move.axes" F"f"\n'
        else:
            return None

        uart.write(command.encode('utf-8'))

        response = ""
        start_time = time.ticks_ms()
        while True:
            if uart.any():
                chunk = uart.read().decode('utf-8')
                response += chunk

            if 'ok' in response:
                print("queried model at:", time.ticks_ms, "response:", response)
                break

            if time.ticks_diff(time.ticks_ms(), start_time) > 1000:
                print("model querying failed at:", time.ticks_ms, "response:", response)
                break

        if object_model in ["move", "move_wcs"]:
            try:
                json_response = response.split("ok")[0]
                data = json.loads(json_response)

                coordinates = []
                for axis in data["result"]:
                    if object_model == "move":
                        coordinates.append(axis["userPosition"])
                    else:
                        coordinates.append(axis["machinePosition"])

                return coordinates[:3]  # Return only X, Y, Z
            except:
                print("Error parsing response")
                raise QueryError("Failed to receive response")

    except Exception as e:
        print(f"Error: {e}")
        raise QueryError(str(e))
    return None
    
encoder_clk.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=lambda p: None)
encoder_dt.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=lambda p: None)
