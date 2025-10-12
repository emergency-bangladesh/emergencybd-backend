# Emergency Bangladesh — Backend

**Framework:** FastAPI
**Database:** SQLCipher (encrypted SQLite)
**Python:** 3.13+

---

## Overview

Emergency Bangladesh (EmergencyBD) is a backend service designed to support a nationwide emergency response platform that connects volunteers and people in need during situations like blood shortages, fires, or missing person incidents.

It focuses on secure data handling, volunteer management, and fast, reliable communication between clients and the backend API.
The commit history of this repository is intentionally hidden, as the core team has chosen not to disclose internal development details.

It is the backbone of [https://emergencybd.com](https://emergencybd.com).

---

## Features

- Secure authentication using JWT and Argon2
- Volunteer verification and regional matching (district/upazila level)
- Encrypted database using SQLCipher
- OTP-based login
- Image upload and management
- Configurable environment settings
- Asynchronous and high-performance API architecture

---

## Tech Stack

| Component      | Technology                     |
| -------------- | ------------------------------ |
| Framework      | FastAPI                        |
| ORM / DB Layer | SQLModel + SQLCipher           |
| Authentication | JWT, Argon2, OTP (pyotp)       |
| Validation     | Pydantic v2, pydantic-settings |
| Media Handling | Pillow, python-multipart       |
| Security       | Cryptography, SQLCipher        |
| Deployment     | Gunicorn                       |
