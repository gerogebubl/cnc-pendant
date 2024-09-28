import machine
import time

class Encoder:
    def __init__(self, clk_pin, dt_pin, debounce_time):
        self.encoder_clk = machine.Pin(clk_pin, machine.Pin.IN, machine.Pin.PULL_UP)
        self.encoder_dt = machine.Pin(dt_pin, machine.Pin.IN, machine.Pin.PULL_UP)
        self.last_encoded = 0
        self.encoder_value = 0
        self.last_update_time = 0
        self.DEBOUNCE_TIME = debounce_time
        self.encoder_steps = 0

    def setup_interrupts(self, callback):
        self.encoder_clk.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=callback)
        self.encoder_dt.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=callback)

    def handle_change(self):
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, self.last_update_time) < self.DEBOUNCE_TIME:
            return 0  # Debounce: ignore changes that occur too quickly

        MSB = self.encoder_clk.value()
        LSB = self.encoder_dt.value()

        encoded = (MSB << 1) | LSB
        diff = (self.last_encoded << 2) | encoded

        if diff == 0b1101 or diff == 0b0100 or diff == 0b0010 or diff == 0b1011:
            self.encoder_steps += 1
            direction = 1
        elif diff == 0b1110 or diff == 0b0111 or diff == 0b0001 or diff == 0b1000:
            self.encoder_steps -= 1
            direction = -1
        else:
            direction = 0

        self.last_encoded = encoded
        self.last_update_time = current_time

        return direction

    def get_steps(self):
        return self.encoder_steps

    def reset_steps(self):
        self.encoder_steps = 0
