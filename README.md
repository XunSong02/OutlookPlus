# OutlookPlus

This repository is just for course: SP26-CS698004.

OutlookPlus is an AI-powered Email Manager featuring a modern, responsive UX (React + Vite) and a powerful AI backend (FastAPI + Google Gemini). It provides AI-based email summaries, sentiment analysis, suggested replies, and background IMAP ingestion.

## Project Structure

This repository contains two main parts:

- **`frontend/`**: The React + Vite application that provides the user interface. Features responsive design, light/dark modes, and accessibility improvements.
- **`backend/`**: A Python-based backend that includes:
  - **API Server** (FastAPI) to handle frontend requests and interface with LLM.
  - **Ingestion Worker** to continuously fetch emails via IMAP and perform offline classification.

---

## Quick Start

To launch the full stack locally, you will need to open terminal windows for both the backend and frontend.

### 1. Set Up the Backend (API Server & Worker)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Set up a Python virtual environment (Python 3.10+ recommended) and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Configure your environment variables:
   Create a `.env` file in the `backend/` folder, you can use ".env tmp" and change the file name. Important variables include:
   - `GEMINI_API_KEY`: Your Google Gemini API key (for AI summarization & replies).
   - `OUTLOOKPLUS_AUTH_MODE=A` (For local demo/dev without auth restrictions).
   -  Add IMAP/SMTP variables (see `backend/README.md` for details).
4. Run the API Server:
   ```bash
   python run_api.py
   ```
   *The backend will be running at `http://127.0.0.1:8000`.*
5. Run the IMAP Ingestion Worker in another terminal:
   ```bash
   python run_worker.py
   ```

### 2. Set Up the Frontend

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node.js dependencies:
   ```bash
   npm install
   ```
3. Start the dev server:
   ```bash
   npm run dev
   ```
   *The frontend will be available at `http://localhost:5173` (or similar).* By default, any `/api` requests will proxy to the backend running at `127.0.0.1:8000`.

## Documentation

For more detailed setup, data storage mechanisms, and specific configurations:
- [Backend Documentation](backend/README.md)
- [Frontend Documentation](frontend/README.md)