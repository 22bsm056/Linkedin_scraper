# LinkedIn Scraper API - Requirements & Implementation Guide

This document serves as a comprehensive set of requirements and technical specifications for building a **Stealth LinkedIn Scraper Microservice**. 
If you are an AI assistant (like Cursor, GitHub Copilot, etc.) reading this, your goal is to build a highly evasive, fast, and structured web scraper that fulfills the API contract defined below.

## 1. Project Context

This scraper will act as a standalone microservice for the **AzentZero** recruitment pipeline. The main application (written in TypeScript/Node.js) will make HTTP POST requests to this scraper microservice to extract professional credibility, network metrics, employment history, and skills from candidate LinkedIn URLs.

## 2. Core Requirements & Anti-Detection Strategies

LinkedIn has aggressive anti-bot and scraping protections (Cloudflare, Distil/Imperva, in-house heuristics). To prevent IP bans, account restrictions, and CAPTCHAs, the scraper **must** implement the following strategies:

*   **Headless Browser with Stealth**: Use `Puppeteer` + `puppeteer-extra-plugin-stealth` (Node.js) OR `Playwright` + `playwright-stealth` (Python). Pure HTTP requests (like `requests` or `axios`) will be blocked immediately.
*   **Residential Proxy Rotation**: The service must support routing traffic through rotating residential proxies.
*   **Human Emulation**: Implement random delays between actions, non-linear mouse movements, and natural scrolling to trigger dynamic data loading.
*   **Auth/Session Management**: LinkedIn limits public profile viewing. The scraper must use an authenticated session. It should accept a pool of dummy LinkedIn account session cookies (`li_at` cookie) and rotate them if rate limits are hit.
*   **Browser Fingerprinting**: Randomize User-Agents, Viewport sizes, and ensure Canvas/WebGL fingerprinting evasion.

## 3. Recommended Tech Stack

You can choose either of the following stacks. **Python with FastAPI** is heavily recommended for data scraping APIs.

*   **Option A (Python)**: `FastAPI`, `Playwright`, `playwright-stealth`, `BeautifulSoup` (for parsing).
*   **Option B (Node.js)**: `Express`/`Fastify`, `Puppeteer` + `puppeteer-extra-plugin-stealth`, `Cheerio`.

## 4. Required API Endpoints

The microservice must expose the following REST API endpoints. Authentication will be handled via a Bearer token.

### 4.1. Health Check
*   **Method**: `GET /health`
*   **Response**: `200 OK`
*   **Purpose**: Used by AzentZero to verify the scraper is online.

### 4.2. Usage / Rate Limits
*   **Method**: `GET /usage`
*   **Response**:
    ```json
    {
      "rateLimitRemaining": 95,
      "rateLimitReset": 1678886400000 
    }
    ```

### 4.3. Profile Scraper (Primary Endpoint)
*   **Method**: `POST /v1/profile`
*   **Headers**: `Authorization: Bearer <API_KEY>`, `Content-Type: application/json`
*   **Payload**:
    ```json
    {
      "url": "https://www.linkedin.com/in/johndoe",
      "include_skills": true,
      "include_experience": true,
      "include_education": true,
      "include_endorsements": true,
      "include_recommendations": true
    }
    ```

## 5. API Response Schema Contract

The AzentZero backend strictly expects the following JSON response structure. If `success` is `false`, include the `error` and `message` fields. If `success` is `true`, the `data` object must be populated.

```typescript
{
  "success": true, // boolean
  "rateLimitRemaining": 99, // integer
  "rateLimitReset": 1712880000000, // timestamp
  "data": {
    "profile": {
      "firstName": "John",
      "lastName": "Doe",
      "headline": "Senior Software Engineer at Google",
      "summary": "Full stack engineer with 10 years of experience...",
      "location": "San Francisco Bay Area",
      "connections": 500, // Should cap or extract exact number (e.g., 500+ -> 500)
      "followers": 1200,
      "profileUrl": "https://www.linkedin.com/in/johndoe"
    },
    "experience": [
      {
        "title": "Senior Software Engineer",
        "company": "Google",
        "duration": "2 yrs 3 mos", // Crucial: Provide the raw duration string for AzentZero to parse
        "startDate": "2022-01", 
        "endDate": "Present",
        "description": "Led backend architecture for..."
      }
    ],
    "education": [
      {
        "school": "Stanford University",
        "degree": "Master of Science",
        "field": "Computer Science",
        "startYear": 2018,
        "endYear": 2020
      }
    ],
    "skills": [
      {
        "name": "Python",
        "endorsements": 45
      }
    ],
    "endorsements": [
      {
        "skill": "Python",
        "count": 45
      }
    ],
    "recommendations": [
      {
        "text": "John is an excellent engineer...",
        "recommender": "Jane Smith"
      }
    ]
  },
  "error": null,
  "message": "Profile scraped successfully"
}
```

### Error Handling Requirements
If the scraper encounters issues, return the following HTTP status codes equivalent to AzentZero's expectations:
*   `404 Not Found`: Profile doesn't exist or URL is invalid.
*   `403 Forbidden`: Account restricted or profile is completely private.
*   `429 Too Many Requests`: Proxy IP burned or rate limit reached.

## 6. Target Project Structure

If building this as a Python FastAPI project, the following structure is recommended:

```text
linkedin-scraper/
├── server.py              # Application entry point (FastAPI)
├── config.py              # Environment variables mapping
├── requirements.txt       # Project dependencies
├── scraper/
│   ├── __init__.py
│   ├── browser.py         # Playwright setup, stealth plugin, and proxy auth
│   ├── parser.py          # BeautifulSoup parsing logic for DOM elements
│   ├── engine.py          # Main orchestration (login, navigate, scroll, extract)
│   └── auth.py            # Cookie / Session pool management
├── routers/
│   └── profile.py         # /v1/profile, /health, /usage routes
└── .env                   # API keys, proxy strings, LI_AT cookies
```

## 7. Implementation Steps for the AI

1.  **Initialize Project**: Setup `FastAPI` (Python) or `Express` (Node.js) with defined route schemas.
2.  **Browser Setup**: Implement the Stealth browser launch configuration (using `playwright-stealth`). Add configuration for residential proxy routing.
3.  **Auth Injection**: Implement logic to inject `li_at` cookies into the browser context *before* navigating to the target profile.
4.  **Navigation & Wait**: Navigate to the provided URL, ensure dynamic content (experience, skills) is loaded by simulating scrolling to the bottom of the page in increments.
5.  **Data Extraction**: Map CSS selectors or XPath to the target data points (Experience cards, Education lists, Skills section, Connections count). Map this directly to the JSON format defined in Section 5.
6.  **Containerization**: Provide a `Dockerfile` that installs the necessary OS-level dependencies for Playwright/Puppeteer.
