import tkinter as tk
import serial
import serial.tools.list_ports
import threading
import time

def threaded_auto_connect(app):
    def task():
        ports = [port.device for port in serial.tools.list_ports.comports()]
        if app.selected_port in ports:
            try:
                ser = serial.Serial(app.selected_port, int(app.selected_baudrate), timeout=1)
                app.is_connected = True
                app.status_label.config(
                    text=f"Auto-connected to {app.selected_port} at {app.selected_baudrate} baud.",
                    fg="green"
                )
                ser.close()
            except Exception:
                app.status_label.config(text="Auto-connect failed", fg="red")
                app.is_connected = False
        else:
            app.status_label.config(text="Selected port not available.", fg="red")
            app.is_connected = False

    threading.Thread(target=task).start()

def threaded_monitor_connection(app):
    def monitor():
        current_ports = [port.device for port in serial.tools.list_ports.comports()]
        if app.selected_port in current_ports:
            if not app.is_connected:
                threaded_auto_connect(app)
            else:
                app.status_label.config(
                    text=f"Connected to {app.selected_port} at {app.selected_baudrate} baud.",
                    fg="green"
                )
        else:
            if app.is_connected:
                app.status_label.config(
                    text=f"Lost connection to {app.selected_port}", fg="red"
                )
                app.is_connected = False
                threaded_auto_connect(app)

        if hasattr(app, "monitor_job"):
            app.after_cancel(app.monitor_job)
        app.monitor_job = app.after(1000, lambda: threaded_monitor_connection(app))

    threading.Thread(target=monitor).start()

def show_settings_popup(app, event):
    settings_menu = tk.Menu(app, tearoff=0)

    # --- Port submenu ---
    port_var = tk.StringVar(value=app.selected_port)
    port_menu = tk.Menu(settings_menu, tearoff=0)
    ports = [port.device for port in serial.tools.list_ports.comports()] or ["No ports found"]
    for p in ports:
        port_menu.add_radiobutton(
            label=p,
            variable=port_var,
            value=p,
            command=lambda: app.after(100, lambda: update_and_connect(app, port_var.get(), app.selected_baudrate))
        )
    settings_menu.add_cascade(label="Select Serial Port", menu=port_menu)

    # --- Baudrate submenu ---
    baud_var = tk.StringVar(value=app.selected_baudrate)
    baud_menu = tk.Menu(settings_menu, tearoff=0)
    baudrates = ["2400", "4800", "9600", "19200", "38400", "57600", "115200"]
    for b in baudrates:
        baud_menu.add_radiobutton(
            label=b,
            variable=baud_var,
            value=b,
            command=lambda: app.after(100, lambda: update_and_connect(app, app.selected_port, baud_var.get()))
        )
    settings_menu.add_cascade(label="Select Baudrate", menu=baud_menu)

    try:
        settings_menu.tk_popup(event.x_root, event.y_root)
    finally:
        settings_menu.grab_release()

def update_and_connect(app, port, baudrate):
    app.selected_port = port
    app.selected_baudrate = baudrate

    def task():
        try:
            ser = serial.Serial(app.selected_port, int(app.selected_baudrate), timeout=1)
            app.status_label.config(
                text=f"Connected to {app.selected_port} at {app.selected_baudrate} baud.", fg="green"
            )
            app.is_connected = True
            ser.close()
        except Exception:
            app.status_label.config(
                text="Connection failed: No Port Found", justify="left", anchor="w", fg="red"
            )
            app.is_connected = False

    threading.Thread(target=task).start()

def fake_event_for_popup(app):
    x = app.winfo_pointerx()
    y = app.winfo_pointery()
    return type('Event', (object,), {"x_root": x, "y_root": y})()


    