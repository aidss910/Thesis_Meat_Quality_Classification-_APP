# 🥩 Meat Quality Classification App

This application is a desktop-based tool built with **Python** and **Tkinter** for classifying the freshness of pork meat using data from gas sensors and UV sensors. It supports real-time data collection via serial communication with an ESP32 and displays classification results using a machine learning model.

---

## 📌 Features

- 🔗 **Serial Communication** with ESP32 for real-time sensor data
- 📊 **Sensor Data Logging** to a local SQLite database
- 🧠 **ML-Based Prediction** (Random Forest or other models)
- 🧪 **30-second Averaging** before classification
- 🎛️ **Prediction Mode** and **Data Collection Mode**
- 📂 **Model Management** with easy loading of `.pkl` files
- 🧾 GUI built with **Tkinter** for user interaction

---

## 🧰 Technologies Used

- Python 3.x
- Tkinter (GUI)
- SQLite3 (Database)
- Scikit-learn (Machine Learning)
- PySerial (Serial Communication)
- Joblib (Model loading/saving)

---

## 🖥️ Application Structure

```plaintext
MeatQualityApp/
├── main.py                   # Main GUI application
├── utility.py                # Shared functions (e.g., gas conversion)
├── settings.py               # Global variables and configuration
├── db_handler.py             # Database interaction logic
├── data_collection.py        # Data acquisition logic
├── prediction.py             # Prediction logic
├── models/
│   └── meat_model.pkl        # Trained ML model
└── database/
    ├── raw_data.db           # Raw sensor readings
    └── predictions.db        # Classification results
