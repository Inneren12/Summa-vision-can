# Summa Vision - System Architecture

## 1. System Overview

Summa Vision is a **B2B SaaS and media platform** for automating Canadian macro-economic data visualization. The system extracts raw data from public sources, scores it via an **LLM gate** for virality potential, and generates **SVG charts** combined with **AI background art** to produce publication-ready visual content.

### Core Value Proposition

Automate the entire pipeline from raw government data → scored, contextualized insight → beautiful, shareable chart graphic — with minimal human intervention.

### High-Level Data Flow

```
┌─────────────────┐     ┌───────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Data Sources    │────▶│  ETL Pipelines │────▶│   LLM Gate       │────▶│  Visual Engine    │
│  (StatCan, CMHC)│     │  (Track A & B) │     │  (Gemini Scoring) │     │  (SVG + AI Art)   │
└─────────────────┘     └───────────────┘     └──────────────────┘     └──────────────────┘
                                                                              │
                                                                              ▼
                                                                    ┌──────────────────┐
                                                                    │  Human-in-the-Loop│
                                                                    │  (Assembly & QA)  │
                                                                    └──────────────────┘
```

---

## 2. ETL Pipelines (The Two Tracks)

The system operates two distinct data ingestion tracks, each designed for a different source profile and cadence.

### Track A: Daily Fast Lane (Automated)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| **Source**      | Statistics Canada Web Data Service (WDS) API — `/getChangedCubeList`   |
| **Cadence**     | Daily, automated                                                       |
| **Constraint**  | Strict maintenance window: **00:00 – 08:30 EST**. Rate limit: **10 req/sec** |

**Flow:**

```
Fetch Metadata ──▶ LLM Virality Scoring ──▶ Fetch Raw Data ──▶ Clean & Store
```

1.  **Fetch Metadata** — Poll the WDS API for newly changed cubes within the maintenance window.
2.  **LLM Virality Scoring** — Pass dataset titles and metadata to the LLM Gate for scoring (see Section 3). Only datasets exceeding the virality threshold proceed.
3.  **Fetch Raw Data** — Retrieve the full data vectors for scored datasets, respecting the 10 req/sec rate limit.
4.  **Clean & Store** — Normalize, validate, and persist the data for downstream chart generation.

### Track B: Deep Dive (Manual/CMHC)

| Attribute       | Detail                                                                 |
|-----------------|------------------------------------------------------------------------|
| **Source**      | CMHC Headless Scraper (Playwright) & Manual StatCan CSV uploads        |
| **Cadence**     | Manual trigger / on-demand                                             |
| **Constraint**  | Must use stealth techniques to bypass Cloudflare/Akamai on CMHC       |

**Flow:**

```
Playwright Scrape / CSV Upload ──▶ Parse & Normalize ──▶ Clean & Store
```

1.  **CMHC Scraping** — A headless Playwright-based scraper navigates the CMHC portal using stealth plugins (e.g., random delays, realistic user-agent rotation, fingerprint spoofing) to avoid bot detection by Cloudflare and Akamai WAFs.
2.  **Manual CSV Upload** — For ad-hoc or historical StatCan datasets not available via the WDS API, CSVs are uploaded through the admin interface.
3.  **Parse & Normalize** — Scraped HTML tables or uploaded CSVs are parsed into the common internal data format.
4.  **Clean & Store** — Data is validated and persisted identically to Track A output.

---

## 3. The LLM Gate (AI Brain)

The LLM Gate is the intelligent filter that determines which datasets are worth visualizing and how they should be presented.

| Attribute       | Detail                                        |
|-----------------|------------------------------------------------|
| **Provider**    | Google Gemini API                              |
| **Input**       | Dataset titles, metadata, and contextual notes |
| **Output**      | Strict JSON payload                            |

### Function

The LLM analyzes dataset titles and metadata, then **scores virality on a scale of 1–10** for the Canadian market. Scoring is weighted toward high-engagement topics:

-   🏠 **Housing** (prices, starts, affordability)
-   📈 **Inflation** (CPI, grocery, energy)
-   💰 **Taxes** (rates, brackets, revenue)

### Output Schema

The LLM Gate returns a strict JSON object for each scored dataset:

```json
{
  "title": "Suggested chart headline for social media",
  "chart_type": "line | bar | area | scatter",
  "virality_score": 8,
  "art_prompt": "A photorealistic Canadian suburb at golden hour with dramatic clouds, negative space in the upper third for chart overlay"
}
```

### Guardrails

-   Only datasets scoring **≥ 7** proceed to the Visual Engine by default (threshold is configurable).
-   The LLM is prompted to return **valid JSON only** — no markdown, no prose.
-   Retry logic with exponential backoff handles transient API failures.

---

## 4. Visual Engine Pipeline

The Visual Engine transforms scored data into publication-ready graphics through a three-step compositing process.

### Step 1: Data Layer (SVG Chart Generation)

| Attribute       | Detail                                      |
|-----------------|----------------------------------------------|
| **Tool**        | Python — Plotly                              |
| **Output**      | Transparent-background SVG chart             |

-   Charts are generated programmatically with **strict styling rules** (brand fonts, color palette, axis formatting).
-   The SVG output has a **transparent background** to allow clean compositing over the AI-generated art layer.
-   Chart type is determined by the LLM Gate's `chart_type` recommendation.

### Step 2: Art Layer (AI Background Generation)

| Attribute       | Detail                                      |
|-----------------|----------------------------------------------|
| **Tool**        | AI Image Generator                           |
| **Input**       | `art_prompt` from the LLM Gate output        |
| **Output**      | Background image with intentional negative space |

-   The art prompt explicitly requests **negative space** in a region suitable for chart overlay (e.g., upper third, left half).
-   Generated images are reviewed for brand consistency and visual quality before proceeding.

### Step 3: Assembly (Human-in-the-Loop Compositing)

| Attribute       | Detail                                      |
|-----------------|----------------------------------------------|
| **Tool**        | Flutter Admin App or Figma                   |
| **Process**     | Manual merge of SVG chart over AI background |

-   A human operator uses the **Flutter-based admin interface** (or Figma for complex layouts) to position the transparent SVG chart over the AI background.
-   Final adjustments include text placement, branding watermarks, and aspect ratio cropping for target platforms (Instagram, LinkedIn, X/Twitter).
-   Approved graphics are exported and queued for publishing.

### End-to-End Visual Pipeline

```
┌────────────────────┐
│  Plotly (Python)    │──▶ Transparent SVG Chart
└────────────────────┘
                              │
                              ▼
                      ┌───────────────┐
                      │   Assembly    │──▶ Final Publication-Ready Graphic
                      │  (Flutter /   │
                      │   Figma)      │
                      └───────────────┘
                              ▲
                              │
┌────────────────────┐
│  AI Image Gen      │──▶ Background with Negative Space
└────────────────────┘
```

---

## 5. Technology Summary

| Layer              | Technology                              |
|--------------------|-----------------------------------------|
| ETL — Track A      | Python, Statistics Canada WDS API       |
| ETL — Track B      | Python, Playwright (stealth mode)       |
| LLM Gate           | Google Gemini API                       |
| Chart Generation   | Python, Plotly (SVG output)             |
| Art Generation     | AI Image Generator                     |
| Assembly           | Flutter Admin App / Figma               |
| Admin Interface    | Flutter                                 |
