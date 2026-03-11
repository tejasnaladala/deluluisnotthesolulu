# deluluisnotthesolulu

A local-first relationship analytics engine that turns chat screenshots into data-driven insights. Drop your DM screenshots, get vibe scores, pattern analysis, and tactical advice -all powered by local LLMs through Ollama. No cloud APIs, no data leaves your machine.

> "past vibe performance is not indicative of future results"

## What It Does

- **Screenshot Ingestion** -Drop chat screenshots from iMessage, Instagram, WhatsApp, Snapchat, or any messaging app. LLaVA vision model extracts and attributes messages automatically.
- **Vibe Scoring** -Weighted algorithm scores each day from -1.0 (cooked) to +1.0 (wedding) based on response times, message length ratios, enthusiasm markers, engagement signals, and ghost penalties.
- **Pattern Detection** -Identifies which words boost/kill vibes, ghost triggers, her enthusiasm triggers, optimal texting times, and response time patterns.
- **Statistical Correlations** -Pearson correlation analysis on day-of-week, time-of-day, message gaps, message length, and double-texting patterns with p-value significance testing.
- **AI Agent Briefing** -Sports commentator persona delivers dramatic analysis of your texting game tape, complete with play-by-play commentary and tactical advice.
- **Terminal Dashboard** -Live dashboard with vibe trajectory graph, DEFCON level (1-5), confidence breakdown, and compact AI briefing.
- **Text Suggestion Engine** -Drafts ghost-proof, vibe-optimized next messages in your writing style with SAFE, BOLD, and WILDCARD options.

## Setup

### Prerequisites
- Python 3.8+
- [Ollama](https://ollama.com) installed and running

### Install Models
```bash
ollama pull qwen2.5:32b    # analysis + commentary
ollama pull minicpm-v:8b     # screenshot OCR
```

### Quick Start

```bash
# 1. Start Ollama
ollama serve

# 2. Seed demo data (optional, for testing)
python seed_mixed_signals.py
python score_vibes.py

# 3. Or ingest real screenshots
#    Drop .png/.jpg files into screenshots/ folder, then:
python ingest.py

# 4. Run the dashboard
python dashboard.py

# 5. Get the full AI briefing
python delulu_detective.py

# 6. Get text suggestions
python suggestion_engine.py

# 7. View correlation analysis
python vibe_correlations.py
```

## Ingesting Real Screenshots

1. Save chat screenshots to the `screenshots/` folder
2. Run `python ingest.py`
3. Messages are extracted, parsed, and inserted into the database
4. Processed screenshots move to `screenshots/processed/`
5. Vibe scores are automatically recalculated

To start fresh: `python ingest.py --reset`

## Project Structure

```
deluluisnotthesolulu/
├── delulu_detective.py     # AI agent briefing (main analysis)
├── dashboard.py            # Terminal dashboard with DEFCON level
├── suggestion_engine.py    # Ghost-proof text suggestion engine
├── ingest.py               # Screenshot ingestion pipeline
├── score_vibes.py          # Vibe scoring algorithm
├── vibe_correlations.py    # Statistical correlation analysis
├── data_engine.py          # Database queries and trend analysis
├── pattern_detector.py     # Pattern recognition engine
├── seed_mixed_signals.py   # Demo data seeder
├── msg_data.json           # Demo conversation templates
├── screenshots/            # Drop screenshots here
│   └── processed/          # Processed screenshots moved here
└── mixed_signals.db        # SQLite database (auto-created)
```

## How Scoring Works

Each day gets a vibe score from -1.0 to +1.0 based on weighted factors:

| Factor | Weight | What It Measures |
|--------|--------|------------------|
| Response Time | 25% | How fast she replies |
| Length Ratio | 20% | Her message length vs yours |
| Ghost Penalty | 15% | Left on read detection |
| Initiation | 15% | Who texted first |
| Enthusiasm | 15% | Exclamation marks, emojis, repeated chars |
| Engagement | 10% | Questions and "you/your" references |

## Disclaimer

This is not financial advice. Past vibe performance is not indicative of future results. deluluisnotthesolulu is not a licensed therapist, relationship counselor, or functioning adult.

---

*powered by love for juice wrld and a $600 mac mini*
