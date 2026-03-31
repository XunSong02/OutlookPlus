# Test Directory

This folder contains all unit test files and test output logs for the OutlookPlus project.

## Test Files

### Frontend (Jest)

| File | Source Under Test | Tests |
|------|-------------------|-------|
| `emails.test.ts` | `frontend/src/app/state/emails.tsx` | 9 |
| `outlookplusApi.test.ts` | `frontend/src/app/services/outlookplusApi.ts` | 12 |

### Backend (Python unittest)

| File | Source Under Test | Tests |
|------|-------------------|-------|
| `test_routes_api.py` | `backend/outlookplus_backend/api/routes.py` | 19 |
| `test_repos_persistence.py` | `backend/outlookplus_backend/persistence/repos.py` | 24 |

## How to Run

### Frontend Tests

```bash
cd frontend
npm install
npm test                # run tests
npm run test:coverage   # run tests + coverage report
```

**Required:** Node.js 18+, npm

**Frameworks:**
- Jest (v30) -- test runner
- ts-jest -- TypeScript support
- jest-environment-jsdom -- browser DOM simulation
- @testing-library/react -- React component testing
- @testing-library/jest-dom -- custom DOM matchers

### Backend Tests

Run from the **project root** directory:

```bash
# Install dependencies
cd backend
pip install -r requirements.txt
pip install coverage
cd ..

# Run tests
PYTHONPATH=backend python -m unittest Test.test_routes_api Test.test_repos_persistence -v

# Run tests with coverage
PYTHONPATH=backend coverage run --source=outlookplus_backend.api.routes,outlookplus_backend.persistence.repos -m unittest Test.test_routes_api Test.test_repos_persistence
coverage report -m
```

On Windows CMD:

```cmd
set PYTHONPATH=backend
python -m unittest Test.test_routes_api Test.test_repos_persistence -v
```

**Required:** Python 3.10+, pip

**Frameworks:**
- unittest -- Python built-in test framework
- coverage -- code coverage measurement

## Test Output Logs

| Log File | Content |
|----------|---------|
| `frontend_test_results.log` | Frontend test run results (21 tests, all PASS) |
| `frontend_coverage_report.log` | Frontend code coverage (outlookplusApi.ts 96%, emails.tsx 93%) |
| `backend_test_results.log` | Backend test run results (43 tests, all OK) |
| `backend_coverage_report.log` | Backend code coverage (routes.py 91%, repos.py 90%, total 91%) |

## Code Coverage Summary

| Source File | Statement Coverage | Target |
|-------------|-------------------|--------|
| `routes.py` | 91% | >= 80% |
| `repos.py` | 90% | >= 80% |
| `outlookplusApi.ts` | 96% | >= 80% |
| `emails.tsx` | 93% | >= 80% |
