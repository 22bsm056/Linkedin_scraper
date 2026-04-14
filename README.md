# LinkedIn Profile Scraper

A robust, high-performance LinkedIn profile scraper designed for production-grade data extraction. It successfully bypasses modern Shadow DOM (SDUI) obstructions, lazy-loading rehydration issues, and handles character encoding for international profiles.

## 🚀 Key Features

- **SDUI Support**: Custom "Greedy Text Extraction" strategy that reliably parses LinkedIn's modern Shadow DOM structure.
- **Parallel Ingestion**: Simultaneously fetches Experience, Education, and Skills in background worker tabs to reduce collection time by ~50%.
- **Asset Blocking**: Intercepts and blocks images, fonts, and media to minimize bandwidth usage and accelerate rendering.
- **Smart Rehydration**: Automated JavaScript scrolling to trigger all lazy-loaded profile sections.
- **Multilingual Ready**: Specialized transliteration layer for Japanese business terminology and emoji sanitization.
- **PDF Generation**: Automatically exports professional, cleaned-up profiles to PDF format.
- **Stealth Mode**: Built-in persistent session management and human-like interaction patterns to evade anti-bot systems.

## 🛠️ Tech Stack

- **Core**: Python 3.10+
- **Browser Automation**: [Playwright](https://playwright.dev/) with [Playwright-Stealth](https://github.com/berstend/playwright-stealth)
- **Parsing**: BeautifulSoup4 (lxml)
- **API Framework**: FastAPI & Uvicorn
- **PDF Export**: FPDF2
- **Environment**: Pydantic-Settings

## 📂 Project Structure

```text
Linkedin_scraper/
├── scraper/              # Core Scraping Logic
│   ├── engine.py         # Orchestration & Navigation
│   ├── parser.py         # SDUI Greedy Parser
│   ├── browser.py        # Process & Asset Management
│   ├── cleaner.py        # Unicode & Transliteration
│   └── exporter.py       # PDF Generation
├── routers/              # API Endpoints
├── server.py             # FastAPI Entrypoint
├── benchmark_profiles.py # Performance Testing Suite
├── config.py             # Configuration Management
└── .env                  # Secrets (Email, Password)
```

## ⚙️ Setup & Installation

1. **Clone the Repository**
2. **Create a Virtual Environment**
   ```powershell
   python -m venv venv311
   .\venv311\Scripts\activate
   ```
3. **Install Dependencies**
   ```powershell
   pip install -r requirements.txt
   playwright install chromium
   ```
4. **Configure Environment**
   Create a `.env` file (refer to `.env.example`):
   ```env
   LINKEDIN_EMAIL=your_email@example.com
   LINKEDIN_PASSWORD=your_password
   ```

## 🏃 Usage

### 📊 Running the Benchmark
Measure performance against a set of complex profiles:
```powershell
venv311\Scripts\python benchmark_profiles.py
```

### 🛰️ Running the API Server
Start the microservice:
```powershell
venv311\Scripts\python server.py
```
Access the Swagger documentation at `http://localhost:8000/docs`.

### 🧪 Integration Test
Scrape a single profile and generate a PDF:
```powershell
venv311\Scripts\python test_scrape.py
```

## 📈 Performance

| Metric | Result |
| :--- | :--- |
| **Success Rate** | 100% |
| **Avg. Time / Profile** | ~43 Seconds |
| **Memory Usage** | Optimized via Asset Blocking |

---

## 🔒 Security Note
This scraper uses **persistent browser contexts**. While it simulates human-like behavior, avoid running excessive batches in short timeframes to protect your LinkedIn account reputation. Always use a dedicated automation account where possible.
