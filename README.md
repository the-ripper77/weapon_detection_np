# Weapon Detection System - Client Side

Welcome to the Client-Side Desktop User Interface for the Weapon Detection System. This application is built using **PyQt5** and **OpenCV**.

---

## Getting Started

Follow these steps to set up your local development environment and run the desktop application.

### Prerequisites

* **Python 3.10+** installed on your system
* An active internet connection (to download dependencies and pre-trained model bases)

---

# 🛠️ Installation & Setup

All commands below assume you are operating from a terminal (such as Windows PowerShell) inside the project root directory:

```powershell
Client Side/
```

---

## Step 1: Create a Virtual Environment

Isolate your project dependencies by creating a dedicated virtual environment named `venv`.

```powershell
python -m venv venv
```

---

## Step 2: Activate the Virtual Environment

Activate the environment to ensure all packages install cleanly inside your local workspace.

### On Windows (PowerShell)

```powershell
.\venv\Scripts\Activate.ps1
```

### On Windows (Command Prompt)

```cmd
.\venv\Scripts\activate.bat
```

### On Linux/macOS

```bash
source venv/bin/activate
```

> You should see `(venv)` appear at the beginning of your terminal prompt once activation is successful.

---

## Step 3: Install Required Dependencies

Upgrade `pip` to the latest version and install all required dependencies listed in `requirements.txt`.

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

# 💻 Running the Application

## Step 4: Launch the Core Application

Once your virtual environment is active and all dependencies are installed, launch the main application:

```powershell
python main.py
```

For Linux/macOS environments, use:

```bash
python3 main.py
```

---
