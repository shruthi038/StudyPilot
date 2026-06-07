# ✈️ StudyPilot

StudyPilot is an AI-powered educational web application designed to help students optimize their learning experience. It combines a **technical chatbot**, a **multi-format notes summarizer**, and a **stress-adaptive study planner** in a custom-styled, premium dark-themed interface.

The application is engineered to operate seamlessly in both **online** (via the Groq API) and **offline** modes (falling back to local machine learning models and similarity-based algorithms).

---

## 🌟 Key Features

### 1. 💬 Ask Anything (Technical Chatbot)
A chatbot helper tailored to Python, Data Structures & Algorithms (DSA), OOP, and Machine Learning.
* **Smart Mode (Online):** Powered by the **Groq API** (running `llama-3.3-70b-versatile`) to generate structured, markdown-rich answers with syntax-highlighted code blocks, lists, and tips.
* **Offline Fallback:** Employs a local **TF-IDF + Cosine Similarity** model mapped against a pre-loaded knowledge base of 100+ common questions.
* **Auto-Correction:** Automatically checks spelling typos in user queries using `difflib.get_close_matches` before matching.
* **Sentiment Analysis:** Monitors the student's emotional state using **NLTK's VADER Sentiment Analyzer**. If a student appears stressed, the UI gives supportive real-time micro-feedback.

### 2. 📝 Notes Summarizer
Allows students to paste long lecture slides, documents, or articles and receive structured summaries.
* **Word Customization:** Customize the output length (between 10 to 1000 words).
* **Multiple Output Formats:** Formats summaries into *Plain Text*, *Bullet Points*, *Essay*, *Letter*, or *Email*.
* **Local Fallback:** Uses Hugging Face's local transformer pipeline (`transformers` with `t5-small`) to generate summary chunks offline when API keys are absent.

### 3. 📅 Adaptive Study Planner
A Pomodoro-style interactive study schedule that adapts dynamically to your mental state:
* **Mood Check-in:** Processes how you are feeling (e.g., *stressed*, *tired*, *excited*) through sentiment analysis.
* **Stress-Adaptive Intervals:**
  * **Gentle Mode (High Stress):** 20 min focus + 10 min recovery breaks (plus encouraging notes reminding you that mental health comes first).
  * **Mellow Mode (Mild Stress):** 25 min focus + 10 min breaks.
  * **Classic Mode (Healthy/Motivated):** 25 min focus + 5 min breaks.
* **Weak-Subject Weighting:** Prioritizes subjects by allocating double slots for your self-declared "Weak Subject".
* **Motivational Engine:** Delivers dynamic, mood-tailored quotes to push you through tough study sessions.

### 4. 🔑 Authentication & Security
* **SQLite Database:** Local user records, chat history, planner schedules, and note summaries are saved inside `studypilot.db`.
* **Password Security:** Credentials are encrypted using SHA-256 before database storage.
* **OTP Verification:** Verification code emails are dispatched during signup and password recovery using Gmail's SMTP servers.

---

## 🛠️ Technology Stack

| Component | Technologies & Libraries |
| :--- | :--- |
| **Frontend UI** | [Streamlit](https://streamlit.io/) + Custom Vanilla CSS (Plus Jakarta Sans typography, custom dark-glass theme) |
| **Database** | [SQLite](https://www.sqlite.org/) |
| **AI LLM Engine (Online)** | [Groq API](https://groq.com/) (`llama-3.3-70b-versatile`) |
| **NLP & Local ML (Offline)** | `nltk` (VADER, tokenizers), `scikit-learn` (TF-IDF, Cosine Similarity), `transformers` (T5-small via PyTorch), `difflib` |
| **Authentication/Mailing** | `smtplib`, `email.mime`, `hashlib` |

---

## 🚀 Installation & Setup

### Prerequisites
* Python 3.9 or higher installed.
* A Gmail account with an **App Password** created (required for SMTP email verification).
* A **Groq API Key** (optional, for online LLM features).

### 1. Clone & Navigate
```bash
git clone https://github.com/Rahul-pamula/StudyPilot.git
cd StudyPilot
```

### 2. Install Dependencies
Install the required packages using pip:
```bash
pip install -r requirements.txt
```
*Note: On the first run, the local NLP models (NLTK lexicons and T5 transformer models) will download automatically.*

### 3. Configure Environment Variables
Create a file named `.env` in the root directory and add your credentials:
```env
# Optional: To use online LLM features
GROQ_API_KEY=your_groq_api_key_here

# Required: To use email verification and password recovery
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
```

### 4. Run the Application
Start the Streamlit development server:
```bash
streamlit run main.py
```

---

## 🎨 Theme & Visual Architecture

StudyPilot is visually customized to override Streamlit's default templates, providing a full-width web app experience:
* **Base styling:** Dark blue-gray palette (`#080C14` background, `#0D1117` cards, `#1E2533` borders).
* **Typography:** Modern, lightweight sans-serif font face `Plus Jakarta Sans`.
* **Animations:** Highlighted action buttons with smooth transitions.
* **Custom Chat Interface:** Styled message bubbles (blue-gradient for user, clean bordered gray container for bot replies) mimicking modern web messaging apps.
