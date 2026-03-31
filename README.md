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
   Create a `.env` file in the `backend/` folder, you can use `.env tmp` and rename it to `.env`. Set the following variables:
   - `GEMINI_API_KEY`: Your Google Gemini API key.
   - `OUTLOOKPLUS_IMAP_USERNAME`: Your email address for IMAP access.
   - `OUTLOOKPLUS_IMAP_PASSWORD`: Your IMAP app password.
   - `OUTLOOKPLUS_SMTP_USERNAME`: Your email address for SMTP sending.
   - `OUTLOOKPLUS_SMTP_PASSWORD`: Your SMTP app password.
   - `OUTLOOKPLUS_AUTH_MODE=A` (for local demo/dev without auth restrictions).

   > This is a public repository. Credentials are not included and must be configured locally before running.

4. Run the API Server:
```bash
   python run_api.py
```
   
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

---

## Running Tests

### Frontend Tests

**Prerequisites:**
- [Node.js](https://nodejs.org/) v18 or higher
- npm (comes with Node.js)

**Frameworks & libraries used:**
- [Jest](https://jestjs.io/) (v30) -- test runner
- [ts-jest](https://kulshekhar.github.io/ts-jest/) -- TypeScript support for Jest
- [jest-environment-jsdom](https://www.npmjs.com/package/jest-environment-jsdom) -- browser DOM simulation
- [@testing-library/react](https://testing-library.com/docs/react-testing-library/intro/) -- React component testing
- [@testing-library/jest-dom](https://github.com/testing-library/jest-dom) -- custom DOM matchers

**Steps:**

1. Navigate to the frontend directory and install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Run the tests:
   ```bash
   npm test
   ```

3. Run the tests with code coverage report:
   ```bash
   npm run test:coverage
   ```

**Test files** are located in `frontend/tests/`:
- `emails.test.ts` -- tests for the emails state management module
- `outlookplusApi.test.ts` -- tests for the API client service

---

### Backend Tests

**Prerequisites:**
- [Python](https://www.python.org/) 3.10 or higher
- pip (comes with Python)

**Frameworks & libraries used:**
- [unittest](https://docs.python.org/3/library/unittest.html) -- Python's built-in test framework (no extra install needed)
- [coverage](https://coverage.readthedocs.io/) -- code coverage measurement

**Steps:**

1. Navigate to the backend directory, set up a virtual environment, and install dependencies:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install coverage
   ```

2. Run the tests from the **project root** directory (not `backend/`):
   ```bash
   cd ..  # back to project root
   PYTHONPATH=backend python -m unittest Test.test_routes_api Test.test_repos_persistence -v
   ```
   On Windows CMD, set the environment variable first:
   ```cmd
   set PYTHONPATH=backend
   python -m unittest Test.test_routes_api Test.test_repos_persistence -v
   ```

3. Run the tests with code coverage report:
   ```bash
   PYTHONPATH=backend coverage run --source=outlookplus_backend.api.routes,outlookplus_backend.persistence.repos -m unittest Test.test_routes_api Test.test_repos_persistence
   coverage report -m
   ```

**Test files** are located in `Test/`:
- `test_routes_api.py` -- unit tests for the REST API route handlers (`routes.py`)
- `test_repos_persistence.py` -- unit tests for the database repository layer (`repos.py`)

---

### Continuous Integration

Both frontend and backend tests run automatically on every push via GitHub Actions:
- `.github/workflows/run-frontend-tests.yml`
- `.github/workflows/run-backend-tests.yml`

---

## Documentation
For more detailed setup, data storage mechanisms, and specific configurations:
- [Backend Documentation](backend/README.md)
- [Frontend Documentation](frontend/README.md)
