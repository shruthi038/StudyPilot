# StudyPilot

StudyPilot is an AI learning companion featuring an AI Tutor, Smart Summarizer, and Adaptive Study Planner.

## Architecture

This project follows an MVC-inspired flat architecture to decouple database logic, Streamlit state management, and external service calls, resulting in a maintainable, professional codebase.

```mermaid
graph TD
    %% Main Entry Point
    Main[main.py (App Shell)] --> Components
    Main --> Pages

    %% Core Layers
    subgraph UI Layer
        Pages[pages/ <br> e.g. home, ai_tutor, planner]
        Components[components/ <br> e.g. sidebar, navbar, cards]
        AuthUI[auth/ <br> e.g. login, signup]
    end

    subgraph Controller Layer
        Controllers[controllers/ <br> auth_controller, chat_controller, etc.]
    end

    subgraph Service Layer
        Services[services/ <br> chatbot, summarizer, planner]
    end

    subgraph Data Layer
        Models[models/ <br> user_model, chat_model, etc.]
        DB[(database.py <br> SQLite)]
    end

    %% Interactions
    Pages --> Controllers
    Components --> Controllers
    AuthUI --> Controllers

    Controllers --> Services
    Controllers --> Models
    Models --> DB
```

### Directory Structure

- `models/`: Database interaction logic (SQLite queries). Decoupled from Streamlit.
- `services/`: Business logic and external API integrations (Groq, NLTK, Scikit-learn). No Streamlit dependencies.
- `controllers/`: Orchestrates data between the UI, models, and services. Manages `st.session_state`.
- `pages/`: UI pages for the application features (Home, AI Tutor, Summarizer, Planner, Analytics, Settings).
- `components/`: Reusable UI components (Sidebar, Navbar, Cards, Activity Timeline).
- `auth/`: User authentication UI flows (Login, Signup, Forgot Password).
- `styles/`: CSS and styling theme logic.
- `utils/`: Constants, helpers, and utilities.

## How to Run

1. Clone the repository.
2. Ensure you have the required dependencies installed (`pip install -r requirements.txt`).
3. Set your Groq API Key and SendGrid API Key in `.env`.
4. Run `streamlit run main.py`.
