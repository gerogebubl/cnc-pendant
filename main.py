import lvgl as lv
import task_handler
import time
from hardware import *
from ui import UI
from encoder import Encoder

# Global variables
current_state = 0
states = ['X', 'Y', 'Z', 'F', 'S']
active_button = 0
feed = 100
step = 1
force_update = False
prev_execution_time = 0
INTERVAL = 10000
communication_ok = True
last_successful_movement = 0

# New variables for bundling movements
pending_movement = 0
last_movement_time = 0
RESPONSE_TIMEOUT = 150
MOVEMENT_TIMEOUT = 250  # ms
BAUD = 152000

# UI setup
ui = UI(states)

# Encoder setup
encoder = Encoder(ENCODER_CLK_PIN, ENCODER_DT_PIN, DEBOUNCE_TIME)

def send_gcode(uart_id, baud_rate, tx_pin, rx_pin, movement):
    global current_state, feed, communication_ok, last_successful_movement, prev_execution_time, timeout_count
    attempt_time = time.ticks_ms()
    try:
        preuart = time.ticks_ms()
        uart = machine.UART(uart_id, baudrate=baud_rate, tx=tx_pin, rx=rx_pin)
        print("uart connection time:", time.ticks_ms() - preuart)
        
        axis = states[current_state]
        if current_state <= 2:  # X, Y, Z
            gcode = f"G91 G1 {axis}{movement} F{feed}\n"
            print("Gcode:", gcode)
            print("time:", time.ticks_ms())
            uart.write(gcode.encode('utf-8'))
            if not wait_for_ok(uart):
                raise Exception("Timeout waiting for response")
            print("G-code sequence sent successfully at time:", time.ticks_ms(), "elapsed time:", time.ticks_ms() - attempt_time)
            communication_ok = True
            last_successful_movement = movement
            
            # Update the right label with the new value
            current_value = float(ui.right_label.get_text())
            new_value = current_value + movement
            ui.update_right_label("{:.2f}".format(new_value))
        else:
            print("Cannot send G-code for F or S states")

    except Exception as e:
        print(f"Error sending G-code: {e}")
        communication_ok = False
        encoder.reset_steps()  # Reset encoder steps on communication failure

def wait_for_ok(uart):
    response = ""
    start_time = time.ticks_ms()
    while True:
        if uart.any():
            chunk = uart.read().decode('utf-8')
            response += chunk
            print("response, chunk:", response, chunk)
        if 'ok' in response:
            return True
        if time.ticks_diff(time.ticks_ms(), start_time) > RESPONSE_TIMEOUT:
            print("Timeout waiting for response")
            return True

def handle_encoder_change(pin):
    global current_state, force_update, active_button, feed, step, prev_execution_time, pending_movement, last_movement_time

    direction = encoder.handle_change()
    
    print("activebutton:", active_button, "prev_execution_time:", prev_execution_time, "pending_movement:", pending_movement, "last_movement_time:", last_movement_time)
    if direction != 0:
        prev_execution_time = time.ticks_ms()
        
    if abs(encoder.get_steps()) == 4:
        if active_button == 0:
            if encoder.get_steps() > 0:
                current_state = (current_state + 1) % len(states)
            else:
                current_state = (current_state - 1) % len(states)
            force_update = True
        elif active_button == 1:
            is_increasing = encoder.get_steps() > 0
            if current_state == 3:  # F (Feed)
                feed = update_value(feed, is_increasing, 10, 10000)
                ui.update_right_label(str(feed))
            elif current_state == 4:  # S (Step)
                step = update_value(step, is_increasing, 0.01, 10)
                ui.update_right_label("{:.2f}".format(step))
            elif current_state <= 2:  # X, Y, Z
                movement = step if is_increasing else -step
                pending_movement += movement
                last_movement_time = time.ticks_ms()

        encoder.reset_steps()

def check_pending_movement(event, user_data):
    global pending_movement, last_movement_time, communication_ok, last_successful_movement
    current_time = time.ticks_ms()
    
    if pending_movement != 0 and time.ticks_diff(current_time, last_movement_time) >= MOVEMENT_TIMEOUT:
        if communication_ok:
            send_gcode(1, BAUD, 1, 2, pending_movement)
        else:
            # If communication failed, revert the pending movement
            pending_movement = -last_successful_movement
        
        pending_movement = 0

def button_pressed(event):
    global active_button
    button = event.get_target_obj()
    if button == ui.left_btn:
        active_button = 0
    elif button == ui.right_btn:
        active_button = 1
    ui.update_button_colors(active_button)

def update_coord(event, user_data):
    global prev_execution_time, INTERVAL, force_update, current_state, feed, step, communication_ok, timeout_count

    current_time = time.ticks_ms()
    ui.update_left_label(states[current_state])
    
    if (time.ticks_diff(current_time, prev_execution_time) >= INTERVAL or force_update):
        print("force_update:", force_update)
        force_update = False
        try:
            if current_state <= 2:  # X, Y, Z
                coordinates = [1, 1, 1]
                coordinates = query_object_model(1, BAUD, 1, 2, "move")
                print("coordinates:", coordinates)
                if coordinates:
                    formatted_coord = "{:.2f}".format(float(coordinates[current_state]))
                    ui.update_right_label(formatted_coord)
                    communication_ok = True
                else:
                    raise Exception("Failed to query coordinates")
            elif current_state == 3:  # F (Feed)
                ui.update_right_label(str(feed))
            elif current_state == 4:  # S (Step)
                ui.update_right_label("{:.2f}".format(step))

        except Exception as e:
            print(f"Error querying object model: {e}")
            communication_ok = False
            encoder.reset_steps()  # Reset encoder steps on communication failure

        prev_execution_time = current_time


# Event setup
ui.add_button_event_cb(button_pressed, button_pressed)
ui.update_button_colors(active_button)

# Set up interrupt for encoder
encoder.setup_interrupts(handle_encoder_change)

# Task handler setup
th = task_handler.TaskHandler()
th.add_event_cb(update_coord, task_handler.TASK_HANDLER_STARTED, None)
th.add_event_cb(check_pending_movement, task_handler.TASK_HANDLER_STARTED, None)
