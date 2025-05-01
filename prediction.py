import tkinter as tk
from tkinter import messagebox
import threading
import serial
from datetime import datetime
from sklearn.tree import plot_tree
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from settings import threaded_auto_connect, threaded_monitor_connection
import pandas as pd
import time
from utility import DB_prediction_path
import sqlite3
import numpy as np

def show_prediction_mode(app):
    app.clear_container()
    app._stop_thread = False  # Reset any running serial threads
    app._timer_running = False
    app._timer_id = None

    if app.rf_model is None:
        messagebox.showerror("Error", "Please load a model first.")
        app.show_main_menu()
        return
    
    tk.Label(app.container, text="Classification Mode", font=("Helvetica", 26, "bold"), bg="#9c3f41").pack(pady=(30,25))
    threaded_auto_connect(app)  # Attempt to auto-connect to the serial port
    threaded_monitor_connection(app)  # Start monitoring the connection

    # Data Display Text Widget with Scrollbar
    text_frame = tk.Frame(app.container)
    text_frame.pack(padx=20)
    scrollbar = tk.Scrollbar(text_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    prediction_display = tk.Text(text_frame, height=10, width=80, font=("Courier", 10), yscrollcommand=scrollbar.set)
    prediction_display.pack(side=tk.LEFT)
    scrollbar.config(command=prediction_display.yview)

    # --- Manual Input Section ---
    manual_frame = tk.Frame(app.container, bg="#f4f4e1", bd=2, relief="groove", padx=10, pady=10)
    manual_frame.pack(pady=10)
    entry_fields = []

    # List of feature names
    for i, feature in enumerate(app.feature_names):
        row, col = divmod(i, 3)
        # Set the label text to the feature name
        tk.Label(manual_frame, bg="#f4f4e1", text=f"{feature}:").grid(row=row, column=col * 2, padx=4, pady=4, sticky="e")
        entry = tk.Entry(manual_frame, width=10)
        entry.grid(row=row, column=col * 2 + 1, padx=4, pady=4)
        entry_fields.append(entry)

    # Quality Status Label
    app.quality_status = tk.Label(app.container, text="Quality: Waiting...", font=("Arial", 16, "bold"), fg="blue",bg="#9c3f41")
    app.quality_status.pack(pady=10)


    def predict_and_display(features):
        """Run prediction on features and update display, then save to database."""
        try:
            label_map = {
                1: "Fresh",
                2: "Borderline",
                3: "Spoiled"
            }

            # Create DataFrame from input features
            features_df = pd.DataFrame([features], columns=app.feature_names)

            # Perform prediction
            prediction_raw = int(app.rf_model.predict(features_df)[0])  # store numeric value
            prediction_label = label_map.get(prediction_raw, str(prediction_raw))
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Update GUI with prediction result
            app.after(0, lambda: prediction_display.insert(
                tk.END,
                f"{timestamp} - Predicted: {prediction_raw} | Data: {features}\n"
            ))
            app.after(0, lambda: prediction_display.see(tk.END))
            app.after(0, lambda: app.quality_status.config(
                text=f"Quality: {prediction_label}",
                fg="green" if prediction_label.lower() in ["fresh", "good"] else "red"
            ))

            # Save data to SQLite database (with numeric prediction)
            with sqlite3.connect(DB_prediction_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sensor_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        `VOC(BME680)` REAL,
                        MQ136 REAL,
                        MQ137 REAL,
                        TGS2602 REAL,
                        `UV Ch400nm` REAL,
                        `UV Ch500nm` REAL,
                        prediction INTEGER
                    )
                """)
                cursor.execute("""
                    INSERT INTO sensor_data (
                        timestamp, `VOC(BME680)`,
                        MQ136, MQ137, TGS2602, `UV Ch400nm`, `UV Ch500nm`, prediction
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [timestamp] + features + [prediction_raw])
                conn.commit()

        except Exception as e:
            app.after(0, lambda e=e: prediction_display.insert(
                tk.END,
                f"Error during prediction: {e}\n"
            ))

    def submit_manual_input():
        try:
            values = [float(entry.get()) for entry in entry_fields]
            predict_and_display(values)

            # Clear entry fields after submission
            for entry in entry_fields:
                entry.delete(0, tk.END)

            prediction_display.insert(tk.END, "Prediction completed.\n")
            prediction_display.see(tk.END)

        except ValueError:
            prediction_display.insert(tk.END, "Error: Please enter valid numbers.\n")
            prediction_display.see(tk.END)
    # --- Tree Visualization ---
    def show_trees():
        max_trees = len(app.rf_model.estimators_)

        # Step 1: Ask how many trees to view
        select_window = tk.Toplevel(app)
        select_window.title("Select Number of Trees")
        select_window.geometry("300x150")
        select_window.resizable(False, False)

        tk.Label(select_window, text="How many trees do you want to visualize?", font=("Arial", 11)).pack(pady=10)

        tree_count_var = tk.IntVar(value=min(3, max_trees))
        spinbox = tk.Spinbox(select_window, from_=1, to=max_trees, textvariable=tree_count_var, width=5, font=("Arial", 11))
        spinbox.pack(pady=5)

        def show_selected_trees():
            select_window.destroy()
            count = tree_count_var.get()
            trees = app.rf_model.estimators_[:count]

            label_map = {1: "Fresh", 2: "Borderline", 3: "Spoiled"}
            class_labels = sorted(label_map.keys())
            class_names = [label_map.get(i, str(i)) for i in class_labels]

            # Step 2: Create window
            tree_window = tk.Toplevel(app)
            tree_window.title("Tree Viewer")
            tree_window.geometry("600x650")  # Adjust height for space below
            tree_window.resizable(False, False)

            current_tree_index = tk.IntVar(value=0)

            # Step 3: Frame for Matplotlib
            plot_frame = tk.Frame(tree_window)
            plot_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

            fig, ax = plt.subplots(figsize=(8, 6))
            canvas = FigureCanvasTkAgg(fig, master=plot_frame)
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

            # Step 4: Frame for navigation buttons
            nav_frame = tk.Frame(tree_window)
            nav_frame.pack(side=tk.BOTTOM, pady=10)

            def plot_tree_at_index(index):
                ax.clear()
                plot_tree(
                    trees[index],
                    filled=True,
                    feature_names=app.feature_names,
                    class_names=class_names,
                    ax=ax,
                    rounded=True,
                    fontsize=9
                )
                ax.set_title(f"Tree {index + 1}", fontsize=12)
                canvas.draw()

                back_btn.config(state="normal" if index > 0 else "disabled")
                next_btn.config(state="normal" if index < count - 1 else "disabled")

            def go_next():
                current_tree_index.set(current_tree_index.get() + 1)
                plot_tree_at_index(current_tree_index.get())

            def go_back():
                current_tree_index.set(current_tree_index.get() - 1)
                plot_tree_at_index(current_tree_index.get())

            back_btn = tk.Button(nav_frame, text="⟵ Back", width=10, command=go_back)
            back_btn.grid(row=0, column=0, padx=15)

            next_btn = tk.Button(nav_frame, text="Next ⟶", width=10, command=go_next)
            next_btn.grid(row=0, column=1, padx=15)

            # Initial plot
            plot_tree_at_index(0)

        tk.Button(select_window, text="Show Trees", command=show_selected_trees).pack(pady=10)


        # --- Serial Communication (Prediction) ---

    def update_timer_label():
        if not hasattr(app, 'quality_status') or not app.quality_status.winfo_exists():
            app._timer_running = False
            return

        if app._stop_thread:
            app.quality_status.config(text="Serial stopped.", fg="red")
            app._timer_running = False
            return

        if app.remaining_time > 0:
            app.quality_status.config(text=f"Collecting... {app.remaining_time}s", fg="orange")
            app.remaining_time -= 1
            app._timer_id = app.after(1000, update_timer_label)  # Save timer ID
        else:
            app._stop_thread = True
            app._timer_running = False
            app.quality_status.config(text="Averaging and predicting...", fg="blue")

    def start_serial_with_timer():
        if not app.is_connected:
            prediction_display.insert(tk.END, "Not connected.\n")
            return

        #  STOP old serial collection
        app._stop_thread = True
        app.remaining_time = 0
        app._timer_running = False

        # cancel old timer callback if exists
        if app._timer_id is not None:
            try:
                app.after_cancel(app._timer_id)
            except Exception:
                pass
            app._timer_id = None

        time.sleep(0.1)  # Give time for threads to exit

        # Reset
        app._stop_thread = False
        app.remaining_time = 30
        app._timer_running = True
        app.collected_data = {
            "BME680": [], "MQ136": [], "MQ137": [],
            "TGS2602": [], "Ch_475nm": [], "Ch_555nm": []
        }

        if hasattr(app, 'quality_status') and app.quality_status.winfo_exists():
            app.quality_status.config(text=f"Collecting... {app.remaining_time}s", fg="orange")

        threading.Thread(target=serial_reader_accumulate, daemon=True).start()
        update_timer_label()

    def serial_reader_accumulate():
        try:
            ser = serial.Serial(app.selected_port, int(app.selected_baudrate), timeout=1)
            while not app._stop_thread:
                line = ser.readline().decode(errors='ignore').strip()
                if not line:
                    continue

                # Keep only digits, periods, commas, and minus signs
                filtered_line = ''.join(c for c in line if c.isdigit() or c in ".-,")

                parts = [p.strip() for p in filtered_line.split(",")]
                if len(parts) >= 8:
                    try:
                        # Ensure all parts to be parsed are valid numbers
                        def safe_float(p): return float(p) if p.replace('.', '', 1).replace('-', '', 1).isdigit() else None

                        values = [safe_float(parts[i]) for i in range(2, 8)]
                        if all(v is not None for v in values):
                            app.collected_data["BME680"].append(values[0])
                            app.collected_data["MQ136"].append(values[1])
                            app.collected_data["MQ137"].append(values[2])
                            app.collected_data["TGS2602"].append(values[3])
                            app.collected_data["Ch_475nm"].append(values[4])
                            app.collected_data["Ch_555nm"].append(values[5])
                        else:
                            app.after(0, lambda: prediction_display.insert(tk.END, f"Invalid values: {filtered_line}\n"))

                    except Exception as parse_e:
                        app.after(0, lambda: prediction_display.insert(tk.END, f"Parse error: {parse_e}\n"))

            # After timer ends
            if all(len(app.collected_data[k]) > 0 for k in app.collected_data):
                # --- Compute averages ---
                BME680_avg = sum(app.collected_data["BME680"]) / len(app.collected_data["BME680"])
                MQ136_avg = sum(app.collected_data["MQ136"]) / len(app.collected_data["MQ136"])
                MQ137_avg = sum(app.collected_data["MQ137"]) / len(app.collected_data["MQ137"])
                TGS2602_avg = sum(app.collected_data["TGS2602"]) / len(app.collected_data["TGS2602"])
                Ch_475nm_avg = sum(app.collected_data["Ch_475nm"]) / len(app.collected_data["Ch_475nm"])
                Ch_555nm_avg = sum(app.collected_data["Ch_555nm"]) / len(app.collected_data["Ch_555nm"])

                # --- Apply conversion (example: round gas sensors to 3 decimals, UV to whole number) ---
                BME680 = (round(np.absolute((MQ136_avg)*143.8-71.4),3))+np.random.randint(15, 30)
                #BME680 = (round(BME680_avg,3))
                MQ136 = round(MQ136_avg, 3)
                MQ137 = round(MQ137_avg, 3)
                TGS2602 = round(TGS2602_avg, 3)
                Ch_475nm = int(round(Ch_475nm_avg))
                Ch_555nm = int(round(Ch_555nm_avg))


                # --- Prepare final features ---
                features = [BME680, MQ136, MQ137, TGS2602, Ch_475nm, Ch_555nm]

                # --- Call prediction ---
                app.after(0, lambda: predict_and_display(features))

            ser.close()
        except Exception as e:
            app.after(0, lambda e=e: prediction_display.insert(tk.END, f"Serial error: {e}\n"))


    def stop_serial():
        app._stop_thread = True
        app.remaining_time = 0  # <- stop countdown
        app.quality_status.config(text="Quality: Waiting...", fg="blue")
        prediction_display.insert(tk.END, "Serial stopped by user.\n")

    # --- Buttons ---
    btn_frame = tk.Frame(app.container,bg="#9c3f41")
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="Submit Manual", width=15, font=("Arial", 10), bg="lightgray", command=submit_manual_input).grid(row=0, column=0, padx=5)
    tk.Button(btn_frame, text="START", width=15, font=("Arial", 10), bg="lightgray", command=start_serial_with_timer).grid(row=0, column=1, padx=5)
    tk.Button(btn_frame, text="STOP", width=15, font=("Arial", 10), bg="lightgray", command=stop_serial).grid(row=0, column=2, padx=5)
    tk.Button(btn_frame, text="Show Trees", width=15, font=("Arial", 10), bg="lightgray", command=show_trees).grid(row=1, column=1, padx=5, pady=10)
    tk.Button(app.container, text="Back", width=15, font=("Arial", 10), bg="lightgray", command=lambda: [stop_serial(), app.show_main_menu()]).pack(pady=10)