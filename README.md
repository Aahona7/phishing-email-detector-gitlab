# SentryMail // Advanced Phishing Email Detector

SentryMail is a high-fidelity, local-first web application designed to dissect emails and detect phishing threats. Built using **Python**, **Flask**, **Regex**, and **Natural Language Processing (NLTK)**, SentryMail scans for standard attack vectors (suspicious links, typosquatted sender domains, high-pressure urgency text, and dangerous attachment formats) and generates a cyber-analyst style threat report using the **Gemini LLM**.

---

## 🚀 Key Features

*   **Heuristic Link Scanner**: Flags IP-address domains, shortened links, non-HTTPS protocols for login fields, mismatched anchor-vs-destination links, and suspicious top-level domains (TLDs).
*   **Spoofed Domain Audit**: Implements Levenshtein Distance checks against popular target brands (e.g. PayPal, Amazon) to detect typosquatting, compares display name keywords to sender domains, and validates DNS MX records.
*   **NLP Urgency Analyzer**: Tokenizes email sentences using NLTK to evaluate structural density and flags high-pressure phrasing, credential requests, and suspicious financial requests.
*   **Payload Extension filter**: Intercepts EML multipart scopes, checking for double-extensions, executable signatures, and macros.
*   **AI Security Assistant**: Integrates with Google Gemini API (`gemini-1.5-flash`) to write natural explanations ("*This email is suspicious because...*"). Includes a robust rule-based markdown explanation fallback if no key is configured.
*   **Live Mailbox Sync (IMAP)**: Securely connect Gmail, Outlook, or Yahoo Mail in real-time to load your recent inbox list and scan emails on-demand.
*   **Premium Glassmorphic Dashboard**: A fully responsive, dark-themed obsidian dashboard featuring animated threat meters, scanning sweeps, and sandboxed HTML email viewers.

---

## 🛠️ Tech Stack

*   **Backend**: Python, Flask, `imaplib` (IMAP client), `email` (MIME parser), `dnspython` (MX records validator)
*   **NLP / Heuristics**: NLTK (Sentence & Word tokenization), BeautifulSoup4 (HTML parsing)
*   **AI Integration**: `google-generativeai` (Gemini API)
*   **Frontend**: HTML5, CSS3 (Custom transitions, keyframe sweeps, responsive grid), Vanilla JS (Fetch API, drag-and-drop file listener)
*   **Testing**: Pytest

---

## 📦 Installation & Setup

Ensure you have Python 3.8+ installed.

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/phishing-email-detector.git
cd phishing-email-detector
```

### 2. Set Up a Virtual Environment
Create and activate a virtual environment to keep dependencies isolated:
**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
*Note: NLTK corpora (punkt, stopwords) will automatically download quietly on application startup.*

### 4. Configuration
Create a `.env` file in the root directory by copying the template variables:
```bash
cp .env.example .env
```
Inside `.env`, configure your development server variables:
```env
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1
GEMINI_API_KEY=your_optional_gemini_key_here
```
*(You can also set or change your Gemini API Key directly within the web application interface settings panel, which is stored securely in your browser's session storage).*

---

## 💻 Running the Application

Start the Flask development server:
```bash
python app.py
```
Or use the Flask CLI:
```bash
flask run --port=5000
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser to access the SentryMail dashboard.

---

## 🧪 Running Automated Tests

A comprehensive unit test suite is included to verify the core heuristics. Run them using:
```bash
pytest -v
```

---

## 🛡️ Security Disclaimer

This is a local security assessment tool designed for educational, analysis, and testing purposes. Do not expose this Flask server directly to the public internet without configuring proper reverse proxies, rate-limiting, and SSL encryption. SentryMail parses IMAP credentials securely and holds them in browser-side execution variables only; it never stores your credentials or email contents on server disks.
