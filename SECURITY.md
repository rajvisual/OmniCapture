# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## Reporting a Vulnerability

The OmniCapture team takes the security of our application, user data, and connected devices seriously.

If you discover a security vulnerability in OmniCapture:

1. **Do not disclose the issue publicly** on GitHub issues, pull requests, or forums.
2. Please report the vulnerability privately to the project maintainers via GitHub Private Vulnerability Reporting or via email.
3. In your report, please include:
   - A description of the vulnerability and its potential impact.
   - Step-by-step reproduction instructions or a minimal proof of concept.
   - Any suggested mitigations or fixes.

### Response Timeline
- You will receive an initial response acknowledging your report within 48 hours.
- A technical assessment and remediation plan will be provided within 5 business days.
- A security release will be published once the patch is thoroughly validated.

---

## Security Best Practices for Users

- **ADB Authorization**: Only accept USB debugging authorization prompts from computers you trust.
- **Wireless ADB**: When using Wireless TCP/IP mode (`adb tcpip 5555`), ensure your phone is connected to a secure, private Wi-Fi network. Anyone on an open/public Wi-Fi network could attempt to connect to port 5555 if device authorization is already granted.
- **Credentials & Tokens**: Never commit or share your `client_secrets.json` or `drive_token.json` files. OmniCapture automatically excludes these in `.gitignore`.
