# OpenAura (AI) 🛡️🧠

> **A local and secure AI assistant that monitors, analyzes, and synthesizes your enterprise activity in real-time, ensuring no data leaves your network.**

![OS](https://img.shields.io/badge/OS-Windows-blue)
![AI](https://img.shields.io/badge/AI-Ollama%20%7C%20Llama%203.2-orange)
![Privacy](https://img.shields.io/badge/Privacy-Local%20First-green)
![Status](https://img.shields.io/badge/Status-In%20Development-red)

## 🚧 Project Status

**⚠️ This software is currently under active development.**
No public executable or installer is available yet. The roadmap focuses on stabilizing the local file monitoring engine and the Llama 3.2 integration before the first public Alpha release.

---

## 📋 Overview

**OpenAura** is an artificial intelligence solution designed for SMEs concerned about data privacy. Unlike cloud solutions, OpenAura runs **locally** on your infrastructure.

It acts as a "dual conscience" for the company:
1.  **The Sentinel (Passive):** Monitors changes in your folders (NAS, Servers) and logs activity without interfering.
2.  **The Analyst (Active):** Uses a local LLM to generate periodic summary reports in natural language.

### ✨ Real-World Example

Instead of boring technical logs (*"File plan_v2.pdf added in /Projects"*), OpenAura understands the context and tells a story.

**The Scenario:**
You drop architectural plans and a lease agreement into a new folder named `/New_Office_Soubise` on your NAS.

**OpenAura's Weekly Report:**
> "📢 **Expansion News:** It looks like the company is moving forward with the new premises project in Soubise!
>
> I detected new architectural plans showing a 500m² showroom on the ground floor and a dedicated R&D lab upstairs. The lease agreement has also been drafted. This marks a significant milestone for our production capacity."

---

## 🚀 Key Features

### 🔒 100% Sovereign & Private
* **Local-First Architecture:** AI models run on your machine.
* **Zero Exfiltration:** Your documents are never sent to a third-party cloud.

### 🧠 Adaptive Intelligence
* **Contextual Understanding:** Transforms raw data (files, folder names) into human-readable business updates.
* **Auto-Configuration:** The future wizard will scan your PC (CPU/RAM/VRAM) to recommend the best model (Tiny, Medium, or Vision).

### 🛡️ Industrial-Grade Security
* **Secret Manager (Keyring):** Passwords and API keys are encrypted in the Windows Credential Manager.
* **Secure Portability:** Configuration files utilize strictly local paths and encrypted credentials.

---

## 🛠️ Architecture

The project is built on a modern stack:

* **GUI:** `CustomTkinter` (Modern interface).
* **AI Backend:** `Ollama` (Local automation).
* **Monitoring:** `Watchdog` (File system surveillance).
* **Database:** `SQLite` (WAL Mode).

---

## 📦 Installation

**Coming Soon:**
OpenAura will be distributed as a standalone portable executable for Windows (`.exe`). No Python knowledge or complex command-line setup will be required.

### Docker Support
* 🐳 **Planned:** A Docker container version is in the roadmap for headless server/NAS deployment.

---

🛡️ License: PolyForm Noncommercial (Free for individuals, Commercial License required for businesses).
