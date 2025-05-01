import os
import sys
import tkinter as tk
from tkinter import ttk
import threading
from PIL import Image, ImageTk  # Add this at the top if using gear icons
from utility import update_time, refresh_model_list, load_selected_model, resource_path, toggle_fullscreen, end_fullscreen
from settings import show_settings_popup, fake_event_for_popup
from data_collection import show_data_collecting_mode
from prediction import show_prediction_mode
from create_model import handle_create_model, show_model_context_menu


class MeatQualityApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Meat Quality App by VBC")
        self.attributes('-fullscreen', True)  # Start in full screen
        self.resizable(True, True)

        # Fullscreen control
        self.fullscreen = True
        self.bind("<F11>", lambda event: toggle_fullscreen(self, event))   # Press F11 to toggle full screen
        self.bind("<Escape>", lambda event: end_fullscreen(self, event))   # Press Esc to exit full screen

        # Serial settings
        self.selected_port = "COM6"
        self.selected_baudrate = "9600"
        self.is_connected = False
        self._stop_thread = False
        self.serial_thread = None
        self.model_loaded = False
        self.rf_model = None
        self.feature_names = ["BME680", "MQ136", "MQ137", "TGS2602", "Ch_475nm", "Ch_555nm"]
        self.quality_status = tk.Label()
        self._timer_running = False
        self._timer_id = None
        self.model_var = tk.StringVar()
        self.model_dropdown = None

        # Footer
        self.footer_frame = tk.Frame(self)
        self.footer_frame.pack(side="bottom", fill="x")
        self.status_label = tk.Label(self.footer_frame, text="Not connected", font=("Arial", 10), fg="red", anchor="w")
        self.status_label.pack(side="left", fill="x", padx=10, pady=5)
        self.time_label = tk.Label(self.footer_frame, font=("Arial", 10), anchor="e")
        self.time_label.pack(side="right", padx=10, pady=5)
        update_time(self.time_label, self)

        # Header
        header_frame = tk.Frame(self, height=35)
        header_frame.pack(side="top", fill="x")
        header_frame.pack_propagate(False)
        self.model_label = tk.Label(header_frame, text=f"Model: {self.model_var.get()}", font=("Arial", 10))
        self.model_label.pack(side="left", fill="x", padx=10)

        # Main container
        self.container = tk.Frame(self, bg="#9c3f41")
        self.container.pack(fill="both", expand=True)

        # Bottom frame to hold gear-style button
        self.bottom_frame = tk.Frame(self, height=25, bg="#9c3f41")
        self.bottom_frame.pack(side="bottom", fill="x")
        # Load gear image (make sure gear.png exists in your project folder)
        gear_image = Image.open(resource_path("gear.png")).resize((30, 30))  # Resize as needed
        gear_icon = ImageTk.PhotoImage(gear_image)
        # Canvas to hold the gear icon
        gear_canvas = tk.Canvas(self.bottom_frame, width=100, height=70, bg="#9c3f41", highlightthickness=0, bd=0)
        gear_canvas.pack(side="left", padx=(2, 0))

        # Place gear icon on canvas
        gear_image_id = gear_canvas.create_image(35, 35, image=gear_icon)
        gear_canvas.tag_bind(gear_image_id, "<Button-1>", self.show_gear_menu)
        # Create a popup menu
        self.gear_menu = tk.Menu(self, tearoff=0)

        self.gear_menu.add_command(
            label="Settings", 
            command=lambda: show_settings_popup(self, fake_event_for_popup(self))
        )
        self.gear_menu.add_command(label="Exit", command=self.quit)
        # Keep reference to avoid garbage collection
        self.gear_icon_ref = gear_icon

        self.show_main_menu()

    def show_main_menu(self):
        self.clear_container()
        frame = tk.Frame(self.container, bg="#9c3f41")
        frame.pack(pady=15)

        tk.Label(frame, text="Meat Quality Classification App", font=("Helvetica", 30,"bold"), bg="#9c3f41").pack(pady=(30, 0),padx=20)
        tk.Label(frame, text="by VBC", font=("Cambria", 18, "italic"), bg="#9c3f41").pack(pady=(0, 30))

        group_frame = tk.Frame(frame, bd=2, bg="#f4f4e1" ,relief="groove",padx=10, pady=10)
        group_frame.pack(pady=10,padx=115)

        tk.Label(group_frame, text="Select Model to Use:", font=("Arial", 12, "bold"), bg="#f4f4e1").pack(pady=5)

        self.model_dropdown = ttk.Combobox(group_frame, textvariable=self.model_var, state="readonly", width=40)
        self.model_dropdown.bind("<Button-3>", lambda event: show_model_context_menu(self, event)) # Right-click binding
        self.model_dropdown.pack(pady=5, padx=92)
        refresh_model_list(self)

        tk.Button(group_frame, text="Load Selected Model", font=("Arial", 10), width=20, height=1,
                  command=lambda: threading.Thread(target=self.threaded_model_load).start()).pack(pady=5)
        tk.Button(group_frame, text="Create Model (Drop CSV)", font=("Arial", 10), width=20, height=1,
                  command=self.create_model).pack(pady=5)

        # Frame to hold buttons side by side
        button_row = tk.Frame(frame, bg="#9c3f41")
        button_row.pack(pady=(15, 70))

        # Styling options
        button_style = {"width": 17, "height": 4, "bg": "#f4f4e1",  "fg": "#000000", 
                        "font": ("Arial", 14, "bold"), "relief": tk.RAISED, "bd": 2, 
                        "activebackground": "#e6e6d4"}

        # Prediction Mode Button
        prediction_button = tk.Button(button_row, text="Classification\nMode", command=lambda: show_prediction_mode(self),**button_style)
        prediction_button.pack(side=tk.LEFT, padx=23)

        # Data Collection Button
        data_button = tk.Button(button_row, text="Data\nCollection", command=lambda: show_data_collecting_mode(self), **button_style)
        data_button.pack(side=tk.RIGHT, padx=23)

    def show_gear_menu(self, event):
        try:
            self.gear_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.gear_menu.grab_release()

    def threaded_model_load(self):
        load_selected_model(self)
        self.model_label.config(text=f"Model: {self.model_var.get()}")

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def back_to_main_menu(self):
        self.clear_container()
        self.show_main_menu()

    def create_model(self):
        handle_create_model(self)
        refresh_model_list(self)


if __name__ == "__main__":
    app = MeatQualityApp()
    app.mainloop()
