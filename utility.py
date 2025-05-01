import os
import time
import joblib
from tkinter import messagebox
import sqlite3


def resource_path(relative_path):
    """Get absolute path relative to the script's location (not current working dir)."""
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

SAVE_FOLDER = resource_path("Database")
os.makedirs(SAVE_FOLDER, exist_ok=True)
DB_PATH = os.path.join(SAVE_FOLDER, "Data_in_db.db")
DB_prediction_path = os.path.join(SAVE_FOLDER, "Prediction.db")

MODEL_DIR = resource_path("Models")
os.makedirs(MODEL_DIR, exist_ok=True)

def update_time(label, app):
    def time_update():
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        label.config(text=current_time)
        app.time_job = app.after(1000, time_update)  # Save job ID to app

    # Cancel previous if already scheduled
    if hasattr(app, "time_job"):
        app.after_cancel(app.time_job)  
    time_update()

def refresh_model_list(app):
        """Refresh the models shown in the dropdown."""
        models = [f for f in os.listdir(MODEL_DIR) if f.endswith(".pkl")]
        current_selection = app.model_var.get()
        if app.model_dropdown:
            app.model_dropdown['values'] = models
        # Maintain previous selection if exists
        if current_selection in models:
            app.model_var.set(current_selection)
        else:
            app.model_var.set("")

def load_selected_model(app):
    """Load the model selected in the dropdown."""
    selected_file = app.model_var.get()
    app.model_label.config(text=f"Model: {app.model_var.get()}", font=("Arial", 10))
    if selected_file:
        try:
            model_path = os.path.join(MODEL_DIR, selected_file)
            app.rf_model = joblib.load(model_path)
            app.model_loaded = True
            messagebox.showinfo("Model Loaded", f"'{selected_file}' is now in use.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load model:\n{str(e)}")
            app.rf_model = None
            app.model_loaded = False
    else:
        messagebox.showwarning("No Model Selected", "Please select a model from the dropdown.")
    
def toggle_fullscreen(app, event=None):
    app.fullscreen = not app.fullscreen
    app.attributes("-fullscreen", app.fullscreen)

def end_fullscreen(app, event=None):
    app.fullscreen = False
    app.attributes("-fullscreen", False)

def init_db(app):

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_data (
                timestamp TEXT,
                Temperature REAL,
                Humidity REAL,
                `VOC(BME680)` REAL,
                MQ136 REAL,
                MQ137 REAL,
                TGS2602 REAL,
                `UV Ch400nm` REAL,
                `UV Ch500nm` REAL
            )
        """)
        conn.commit()

def init_db_prediction(app):
    with sqlite3.connect(DB_prediction_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prediction_data (
                timestamp TEXT,
                Temperature REAL,
                Humidity REAL,
                `VOC(BME680)` REAL,
                MQ136 REAL,
                MQ137 REAL,
                TGS2602 REAL,
                `UV Ch400nm` REAL,
                `UV Ch500nm` REAL,
                Quality TEXT
            )
        """)
        conn.commit()

    