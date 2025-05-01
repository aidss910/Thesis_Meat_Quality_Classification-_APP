from tkinter import filedialog
import tkinter as tk
import os
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from tkinter import messagebox, simpledialog
from utility import refresh_model_list, MODEL_DIR

def handle_create_model(app):
    file_path = filedialog.askopenfilename(title="Select CSV File", filetypes=[("CSV files", "*.csv")])
    if not file_path:
        return
    try:
        df = pd.read_csv(file_path)
        required_columns = app.feature_names + ['Label']
        if not all(col in df.columns for col in required_columns):
            messagebox.showerror("Error", f"CSV must contain: {', '.join(required_columns)}")
            return
        model_name = simpledialog.askstring("Model Name", "Enter a name for this model:")
        if not model_name:
            return
        model_path = os.path.join(MODEL_DIR, f"{model_name}.pkl")
        X = df[app.feature_names]
        y = df['Label']
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)
        joblib.dump(model, model_path)
        messagebox.showinfo("Success", f"Model '{model_name}' saved successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to create model:\n{str(e)}")

def show_model_context_menu(app, event):
    models = [f for f in os.listdir(MODEL_DIR) if f.endswith(".pkl")]

    menu = tk.Menu(app, tearoff=0)

    # Submenu for delete
    delete_menu = tk.Menu(menu, tearoff=0)
    for model in models:
        delete_menu.add_command(label=model, command=lambda m=model: delete_model_by_name(app,m))
    menu.add_cascade(label="Delete Model", menu=delete_menu)

    # Submenu for rename
    rename_menu = tk.Menu(menu, tearoff=0)
    for model in models:
        rename_menu.add_command(label=model, command=lambda m=model: rename_model_by_name(app, m))
    menu.add_cascade(label="Rename Model", menu=rename_menu)

    menu.post(event.x_root, event.y_root)

def delete_model_by_name(app, model_name):
    confirm = messagebox.askyesno("Delete Model", f"Delete '{model_name}'?")
    if confirm:
        os.remove(os.path.join(MODEL_DIR, model_name))
        refresh_model_list(app)

def rename_model_by_name(app, model_name):
    new_name = simpledialog.askstring("Rename Model", f"Rename '{model_name}' to:")
    if new_name:
        if not new_name.endswith(".pkl"):
            new_name += ".pkl"
        os.rename(os.path.join(MODEL_DIR, model_name), os.path.join(MODEL_DIR, new_name))
        refresh_model_list(app)