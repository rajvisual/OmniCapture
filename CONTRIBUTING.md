# Contributing to OmniCapture

Thank you for your interest in contributing to **OmniCapture**! We welcome community contributions, bug reports, feature suggestions, and documentation improvements.

---

## 📋 Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please maintain a welcoming, respectful, and collaborative environment.

---

## 🛠️ How to Contribute

### 1. Reporting Bugs
- Search existing issues to ensure the bug has not already been reported.
- Open a new issue with a clear title and description.
- Include:
  - Windows version and PowerShell / Terminal version.
  - Android device brand, model, and Android OS version.
  - Connection type (USB 2.0 / USB 3.0 / Wi-Fi).
  - Exact command executed.
  - Complete terminal error output and logs.

### 2. Suggesting Enhancements
- Open a feature request issue describing the enhancement.
- Explain the real-world use case and how it benefits users.
- Outline possible implementation ideas or technical constraints.

### 3. Submitting Code Changes

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/rajvisual/OmniCapture.git
   cd OmniCapture
   ```
3. **Create a topic branch**:
   ```bash
   git checkout -b feature/my-new-feature
   ```
4. **Set up your Python virtual environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
5. **Implement your changes**:
   - Write clean, readable, documented Python code conforming to PEP 8 standards.
   - Maintain compatibility with Python 3.10+.
   - Ensure changes run properly on Windows.
6. **Run tests**:
   ```powershell
   python -m unittest discover -s tests
   ```
7. **Commit your changes**:
   ```bash
   git commit -m "feat: add support for custom camera fps profiles"
   ```
8. **Push to your fork and submit a Pull Request**:
   ```bash
   git push origin feature/my-new-feature
   ```

---

## 🧪 Testing Guidelines

- All Python code must compile with zero errors: `python -m py_compile omni.py core/*.py`.
- Do not commit sensitive files, personal file paths, tokens, or video recordings.
- Maintain documentation integrity when changing command flags or configuration options.
