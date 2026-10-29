# Safe Model Switch ⚖️

> **Cost & Quality Evaluation Proxy for Safely Migrating LLM Workloads**  
> Total Cost: **₹0 / $0**. Runs 100% locally on your laptop using free software and free-tier APIs.

---

## 1. Project Overview

Companies paying for AI APIs like Google Gemini or OpenAI ChatGPT watch their bills rise with volume. While cheaper alternative models exist (e.g., Llama on Groq), engineering teams hesitate to migrate out of fear that answer quality will drop.

**Safe Model Switch** solves this dilemma:
1. Sits between the client app and the AI, logging all prompts and answers from the current model (**Model A / Gemini**).
2. Uses a **replay engine** to send the exact same queries to the cheaper candidate model (**Model B / Groq**).
3. Uses an **automated evaluator** (combining fast exact-match detection and a strict **LLM-as-a-Judge**) to grade quality from 1 to 5 with an explicit reason.
4. Generates an interactive dashboard with a clear decision banner:
   - **$\ge 90\%$ Quality Retained:** `Safe to switch` (Green)
   - **$75\% - 89\%$ Quality Retained:** `Review needed` (Amber)
   - **$< 75\%$ Quality Retained:** `Not safe` (Red)

---

## 2. System Architecture

```text
 +-----------+     +--------------------------------------------------+
 |  Client   | --> |                 FastAPI Gateway                  |
 | (App/curl)|     | 1. Check API key (SHA-256 hash in SQLite)        |
 +-----------+     | 2. Sliding window rate limiter (e.g. 10 req/min) |
       ^           | 3. Call Model A (Gemini API via httpx)           |
       |           | 4. Log prompt, answer, tokens, latency, est. cost|
       |           +-------------------------+------------------------+
       +--- answer --------------------------+
                                             v
                               +-----------------------------+
                               |     SQLite (gateway.db)     |
                               |  api_keys | requests        |
                               |  replays  | scores          |
                               +--------------+--------------+
                                              |
      POST /replay                            v
 +--------------------+       +------------------------------+
 |   Replay Engine    | ----> |        Model B (Groq)        |
 |   Last N prompts   |       |       (Candidate model)      |
 +--------------------+       +---------------+--------------+
                                              |
                                              v
                              +------------------------------+
                              |    Scorer (POST /score)      |
                              | 1) Exact match check (5/5)   |
                              | 2) LLM Judge (Gemini 1-5)    |
                              +---------------+--------------+
                                              |
                                              v
                              +------------------------------+
                              |     GET /report & Streamlit  |
                              |     Decision banner + KPIs   |
                              +------------------------------+
```

---

## 3. Tech Stack (100% Free)

- **Language:** Python 3.11+
- **Backend:** FastAPI + Uvicorn (Interactive Swagger UI at `/docs`)
- **Data Validation:** Pydantic v2
- **Database:** SQLite with SQLAlchemy ORM (file-based `gateway.db`, no server needed)
- **Model A (Current):** Google Gemini 1.5 Flash (Free tier via Google AI Studio)
- **Model B (Candidate):** Groq API (Llama 3.1 8B Instant via console.groq.com)
- **Judge Model:** Google Gemini 1.5 Pro (Free tier)
- **HTTP Client:** `httpx` (async)
- **Rate Limiting:** In-memory 60-second sliding window timestamp tracker (No Redis)
- **Dashboard:** Streamlit + Pandas
- **Testing:** `pytest`

---

## 4. Setup & Installation

### Step 1: Clone & Navigate
```bash
git clone <your-repo-url>
cd safe-model-switch
```

### Step 2: Create Virtual Environment & Install Dependencies
```bash
python -m venv venv

# Windows:
.\venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and insert your free API keys:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
MODEL_A=gemini-1.5-flash
MODEL_B=llama-3.1-8b-instant
JUDGE_MODEL=gemini-1.5-pro
DATABASE_URL=sqlite:///./gateway.db
DEFAULT_RATE_LIMIT_PER_MIN=10
REPLAY_DELAY_SECONDS=2
```

---

## 5. Running the Project

### 1. Create an API Key
Generate an authorized API key for client requests:
```bash
python scripts/create_key.py "demo-client" 10
```
*Note down the generated plain key (e.g. `sms_...`).*

### 2. Start the FastAPI Gateway
```bash
uvicorn app.main:app --reload
```
- Gateway runs at: `http://127.0.0.1:8000`
- API Health Check: `http://127.0.0.1:8000/health`
- Swagger Documentation: `http://127.0.0.1:8000/docs`

### 3. Seed Sample Requests (Optional Demo Helper)
Send 20 diverse evaluation prompts through the gateway:
```bash
python scripts/seed_prompts.py <your_plain_api_key>
```

### 4. Start the Streamlit Dashboard
In a second terminal window:
```bash
streamlit run dashboard/app.py
```
Open `http://localhost:8501` to view the decision banner, metrics, and side-by-side comparisons.

---

## 6. API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Returns `{"status": "ok"}` |
| `POST` | `/chat` | Takes `{ "prompt": "..." }`, checks `X-API-Key`, logs to SQLite, returns answer & cost |
| `GET` | `/logs?limit=20` | Returns recent logged requests |
| `POST` | `/replay` | Re-runs the last $N$ prompts through Model B (Groq) |
| `POST` | `/score` | Runs exact match + LLM judge scoring on all unscored replays |
| `GET` | `/report` | Returns aggregated metrics, cost savings %, quality retained %, and final verdict |

---

## 7. Running Tests
Run the automated test suite:
```bash
pytest -v
```
All 11 unit tests verify:
- API key authentication (`test_auth.py`)
- In-memory sliding-window rate limiting (`test_rate_limit.py`)
- SQLite logging (`test_logging.py`)
- Token cost calculations (`test_cost.py`)
- Verdict thresholds and JSON judge parsing (`test_verdict.py`)

---

## 8. Honest Limitations & Fairness Note

1. **AI Judge Subjectivity:** The evaluator is also an LLM. While a strict rubric and distinct model are used, LLM judges can carry subtle biases (e.g. favoring specific formatting). For full transparency, the dashboard **never** shows a score without its accompanying reason.
2. **Uncertain Scores:** If the judge outputs an unparseable format, the record is flagged as `Uncertain` and excluded from quality percentage rather than guessed.
3. **Estimated vs Real Cost:** Free API tiers cost ₹0. All displayed costs are calculations based on providers' published per-1M token rates to simulate paid production spend.

---

## 9. Future Upgrades (Post-MVP)
- Semantic response caching (Vector DB / embeddings)
- Automatic fallback routing when provider rate limits are reached
- Per-key budget caps with automated degradation
- Slack / Discord webhook alerts on quality drops
