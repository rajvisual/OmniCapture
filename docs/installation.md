# Installation Guide

This guide provides step-by-step instructions for setting up **OmniCapture** on Windows 10 and Windows 11.

---

## 💻 System Requirements

- **Operating System**: Windows 10 (Build 1809+) or Windows 11 (64-bit).
- **Python**: Python 3.10, 3.11, or 3.12 (with `Add python.exe to PATH` checked during setup).
- **Android Device**: Android 8.0 or higher for screen mirroring; Android 12.0 or higher for low-level background camera capture.
- **Connection**: USB 2.0 / USB 3.0 cable, or local 2.4GHz / 5GHz Wi-Fi network.

---

## 📱 Android Device Preparation

Before connecting your Android phone to your PC, enable developer debugging:

### 1. Enable Developer Options
1. On your phone, navigate to **Settings** > **About Phone**.
2. Tap **Build Number** (or **OS Version / MIUI Version**) **7 times** consecutively until the screen displays *"You are now a developer!"*.

### 2. Enable USB Debugging
1. Go to **Settings** > **System** (or **Additional Settings**) > **Developer Options**.
2. Locate the **Debugging** section.
3. Turn **ON** 👉 **USB Debugging**.
4. Connect your phone to your PC using a USB cable.
5. On your phone's display, accept the prompt **"Allow USB Debugging?"** and check **"Always allow from this computer"**.

### 3. Xiaomi / POCO / Redmi Users (Crucial for Touch Control)
Xiaomi MIUI and HyperOS enforce an extra security restriction that blocks touch clicks and keyboard typing over USB unless explicitly authorized:
1. In **Developer Options**, scroll down to the **Debugging** section.
2. Turn **ON** 👉 **`USB debugging (Security settings)`**  
   *(Subtitle: "Allow granting permissions and simulating input via USB debugging")*.
3. Complete the three 5-second countdown prompts (*Next ➔ Next ➔ Accept*).

*(Alternatively, you can launch OmniCapture with the `--uhid` flag to simulate a hardware USB mouse without modifying this phone setting).*

---

## 📥 Project Installation

### Step 1: Clone the Repository
Open PowerShell or Command Prompt:

```powershell
git clone https://github.com/rajvisual/OmniCapture.git
cd OmniCapture
```

### Step 2: Set Up Python Virtual Environment (Recommended)

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

> [!TIP]
> If PowerShell blocks script execution with an ExecutionPolicy error, run:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
> ```

### Step 3: Install Dependencies

For standard screen mirroring, remote control, and Google Drive for Desktop sync, **no external Python packages are required** (uses Python's standard library).

If you plan to use direct Google Drive REST API OAuth cloud uploads:
```powershell
pip install -r requirements.txt
```

---

## ⚡ Verifying Your Installation

With your phone plugged in, run:

```powershell
python omni.py info
```

If setup correctly, OmniCapture will print your device model, current battery percentage, Wi-Fi IP address, and available camera sensor IDs.
