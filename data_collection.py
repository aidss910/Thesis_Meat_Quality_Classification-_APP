import csv
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
import sqlite3
import serial
import time
from settings import threaded_auto_connect, threaded_monitor_connection
from utility import init_db , DB_PATH

def show_data_collecting_mode(app):
    app.clear_container()
    app._stop_thread = False
    init_db(app)

    threaded_monitor_connection(app)
    threaded_auto_connect(app)

    # Title
    tk.Label(app.container, text="Data Collecting Mode", font=("Helvetica", 26, "bold"), bg="#9c3f41").pack(pady=(30,25))
    status_label = tk.Label(app.container, text="", font=("Arial", 11), fg="blue", bg="#9c3f41")
    status_label.pack()

    # Display area
    text_frame = tk.Frame(app.container)
    text_frame.pack(padx=20)
    scrollbar = tk.Scrollbar(text_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    data_display = tk.Text(text_frame, height=10, width=80, font=("Courier", 10), yscrollcommand=scrollbar.set)
    data_display.pack(side=tk.LEFT)
    scrollbar.config(command=data_display.yview)

    # Manual Input Fields
    manual_frame = tk.Frame(app.container, bg="#f4f4e1", bd=2, relief="groove", padx=30, pady=10)
    manual_frame.pack(pady=10)
    entry_fields = []
    field_labels = [
        "Temperature", "Humidity", "VOC(BME680)", "MQ136",
        "MQ137", "TGS2602", "UV Ch400nm", "UV Ch500nm"
    ]

    for i, label_text in enumerate(field_labels):
        row, col = i % 4, (i // 4) * 2
        tk.Label(manual_frame, bg="#f4f4e1", text=f"{label_text}:").grid(row=row, column=col, sticky="e", padx=4, pady=4)
        entry = tk.Entry(manual_frame, width=12)
        entry.grid(row=row, column=col + 1, padx=4, pady=4)
        entry_fields.append(entry)

    # Manual Submit
    def submit_manual_data():
        try:
            values = [float(entry.get()) for entry in entry_fields]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sensor_data (
                        timestamp, Temperature, Humidity, `VOC(BME680)`,
                        MQ136, MQ137, TGS2602, `UV Ch400nm`, `UV Ch500nm`)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [timestamp] + values)

            data_display.insert(tk.END, f"{timestamp} - Manual Entry: {values}\n")
            data_display.see(tk.END)

        except ValueError:
            data_display.insert(tk.END, "Error: Please enter valid numbers.\n")
            data_display.see(tk.END)

        # Clear entries whether successful or not
        for entry in entry_fields:
            entry.delete(0, tk.END)

    # Save CSV
    def save_to_csv():
        file_name = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="collected_data.csv"
        )
        if not file_name:
            data_display.insert(tk.END, "Save operation cancelled.\n")
            return

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sensor_data")
            rows = cursor.fetchall()

        if not rows:
            data_display.insert(tk.END, "Error: No data to save.\n")
            return

        with open(file_name, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp"] + field_labels)
            writer.writerows(rows)

        data_display.insert(tk.END, f"Data saved to {file_name}\n")
        data_display.see(tk.END)

    # Serial Read Thread
    def read_serial_data():
        try:
            ser = serial.Serial(app.selected_port, int(app.selected_baudrate), timeout=1)
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            while not app._stop_thread:
                start_time = time.time()
                end_time = start_time + app.collection_duration
                collected = []

                # Collect raw data during the duration window
                while time.time() < end_time and not app._stop_thread:
                    try:
                        line = ser.readline().decode(errors='ignore').strip()
                        if not line:
                            continue

                        # Filter out non-numeric, non-comma characters
                        filtered_line = ''.join(c for c in line if c.isdigit() or c in ".-,")
                        parts = [p.strip() for p in filtered_line.split(",")]

                        # Convert to float and ensure correct number of parts
                        if len(parts) == 8 and all(p.replace('.', '', 1).replace('-', '', 1).isdigit() for p in parts):
                            numeric_parts = [float(p) for p in parts]
                            collected.append(numeric_parts)

                    except Exception as inner_e:
                        data_display.insert(tk.END, f"[Read Error] {inner_e}\n")
                        data_display.see(tk.END)


                # If we got data, calculate average and convert it
                if collected:
                    avg = [sum(x[i] for x in collected) / len(collected) for i in range(8)]

                    # Optional conversion logic — replace these as needed
                    def convert(val, label):
                        if label == "Temperature":
                            fahrenheit = (val * 9/5) + 32
                            return round(fahrenheit, 2)
                        elif label == "Humidity":
                            return round(val, 2)
                        elif label in ["VOC(BME680)", "MQ136", "MQ137", "TGS2602"]:
                            return round(val, 3)
                        else:  # UV Channels
                            return val

                    field_labels = [
                        "Temperature", "Humidity", "VOC(BME680)", "MQ136",
                        "MQ137", "TGS2602", "UV Ch400nm", "UV Ch500nm"
                    ]

                    converted = [convert(val, field_labels[i]) for i, val in enumerate(avg)]
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # Save only converted averages to database
                    cursor.execute("""
                        INSERT INTO sensor_data (
                            timestamp, Temperature, Humidity, `VOC(BME680)`,
                            MQ136, MQ137, TGS2602, `UV Ch400nm`, `UV Ch500nm`)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [timestamp] + converted)
                    conn.commit()

                    # Log to display
                    display_line = f"{timestamp} - Averaged + Converted: {converted}"
                    data_display.insert(tk.END, display_line + "\n")
                    data_display.see(tk.END)

                # Wait until next interval
                if not app._stop_thread:
                    sleep_time = max(0, app.collection_interval - app.collection_duration)
                    for _ in range(sleep_time):
                        if app._stop_thread:
                            break
                        time.sleep(1)

            ser.close()
            conn.close()

        except Exception as e:
            data_display.insert(tk.END, f"[Connection Error] {e}\n")
            data_display.see(tk.END)
    #  Start  Stop Thread
    def show_settings_popup():
        popup = tk.Toplevel(app)
        popup.title("Collection Settings")
        popup.geometry("300x140")
        popup.grab_set()  # make it modal

        tk.Label(popup, text="Collect for (seconds):").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        duration_entry = tk.Entry(popup, width=10)
        duration_entry.grid(row=0, column=1)
        duration_entry.insert(0, "30")

        tk.Label(popup, text="Every (seconds):").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        interval_entry = tk.Entry(popup, width=10)
        interval_entry.grid(row=1, column=1)
        interval_entry.insert(0, "240")

        def on_confirm():
            try:
                duration = int(duration_entry.get())
                interval = int(interval_entry.get())

                if duration <= 0 or interval <= 0:
                    raise ValueError("Values must be greater than 0.")
                if duration > interval:
                    raise ValueError("Duration cannot be greater than interval.")

                app.collection_duration = duration
                app.collection_interval = interval

                if app.serial_thread and app.serial_thread.is_alive():
                    message = "Serial thread already running."
                    data_display.insert(tk.END, message + "\n")
                    status_label.config(text=message)
                else:
                    app._stop_thread = False
                    app.serial_thread = threading.Thread(target=read_serial_data, daemon=True)
                    app.serial_thread.start()
                    message = f"Started collection: {duration}s every {interval}s."
                    data_display.insert(tk.END, message + "\n")
                    status_label.config(text=message)

                data_display.see(tk.END)
                popup.destroy()

            except ValueError as ve:
                messagebox.showerror("Invalid Input", str(ve))

        tk.Button(popup, text="Start", width=10, bg="lightgreen", command=on_confirm).grid(row=2, column=0, columnspan=2, pady=15)

    def stop_collection():
        app._stop_thread = True
        message = "Serial collection stopped."
        data_display.insert(tk.END, message + "\n")
        data_display.see(tk.END)
        status_label.config(text=message)

    # Buttons
    btn_frame = tk.Frame(app.container,bg="#9c3f41")
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="Start Serial", width=15, font=("Arial", 10),
            bg="lightgreen", command=show_settings_popup).grid(row=0, column=0, padx=5)
    tk.Button(btn_frame, text="Stop Serial", width=15, font=("Arial", 10),
              bg="tomato", command=stop_collection).grid(row=0, column=1, padx=5)
    tk.Button(btn_frame, text="Submit Manual", width=15, font=("Arial", 10),
              bg="#9c3f41", command=submit_manual_data).grid(row=0, column=2, padx=5)
    tk.Button(btn_frame, text="Save to CSV", width=15, font=("Arial", 10),
              bg="lightyellow", command=save_to_csv).grid(row=1, column=1, pady=10)
    tk.Button(app.container, text="Back", width=15, font=("Arial", 10),
              bg="lightgray", command=lambda: [stop_collection(), app.show_main_menu()]).pack(pady=10)

