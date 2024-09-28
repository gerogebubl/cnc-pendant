import lvgl as lv

class UI:
    def __init__(self, states):
        self.scr = lv.obj()
        lv.screen_load(self.scr)

        self.left_btn = lv.button(self.scr)
        self.left_btn.align(lv.ALIGN.CENTER, -75, 0)
        self.left_btn.set_size(50, 50)
        self.left_label = lv.label(self.left_btn)
        self.left_label.set_text(states[0])
        self.left_label.center()
        self.left_label.set_style_text_font(lv.font_montserrat_48, 0)

        self.right_btn = lv.button(self.scr)
        self.right_btn.align(lv.ALIGN.CENTER, 25, 0)
        self.right_btn.set_size(145, 50)
        self.right_label = lv.label(self.right_btn)
        self.right_label.set_text("0000.00")
        self.right_label.center()
        self.right_label.set_style_text_font(lv.font_montserrat_32, 0)

    def update_button_colors(self, active_button):
        self.left_btn.set_style_bg_color(lv.color_t(lv.palette_main(lv.PALETTE.ORANGE) if active_button == 1 else lv.palette_main(lv.PALETTE.GREEN)), 0)
        self.right_btn.set_style_bg_color(lv.color_t(lv.palette_main(lv.PALETTE.ORANGE) if active_button == 0 else lv.palette_main(lv.PALETTE.GREEN)), 0)

    def update_left_label(self, text):
        self.left_label.set_text(text)

    def update_right_label(self, text):
        self.right_label.set_text(text)

    def add_button_event_cb(self, left_cb, right_cb):
        self.left_btn.add_event_cb(left_cb, lv.EVENT.CLICKED, None)
        self.right_btn.add_event_cb(right_cb, lv.EVENT.CLICKED, None)
