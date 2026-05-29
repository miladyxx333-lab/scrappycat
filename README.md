# 🐱 ScrappyCat

```
 /\_____/\
( o   o  )   ScrappyCat
 =( Y )=     The lead scraper that never stops chasing.
  )   (      Maps → Phone · WhatsApp · Email
 (_)-(_)
```

> Built for indie devs who need real leads — not excuses.

ScrappyCat hunts businesses on Google Maps and hands you their phone, WhatsApp link, and email in a clean CSV. No Docker. No cloud. Just a cat doing its job.

---

## ✨ What it grabs

| Field | Example |
|-------|---------|
| Name | Restaurante Apache Xalapa |
| Phone | 2282029090 |
| WhatsApp | https://wa.me/522282029090 |
| Email | hola@apacherestaurante.com |
| Address | Av. Xalapa 123, Veracruz |
| Website | https://apacherestaurante.com |
| Rating | 4.5 |
| Maps URL | https://maps.google.com/... |

---

## 🚀 Install

**Requirements:** Python 3.8+ · Google Chrome

```bash
git clone https://github.com/miladyxx333-lab/scrappycat.git
cd scrappycat
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

---

## 🎯 Usage

### Single search
```bash
python scrappycat.py search "restaurantes en Xalapa Veracruz"
python scrappycat.py search "dentistas en Monterrey" --limit 50
python scrappycat.py search "gyms en CDMX" --output output/gyms.csv
```

### Batch — multiple queries from a file
```bash
# queries.txt (one per line):
# restaurantes en Xalapa Veracruz
# cafeterias en Xalapa Veracruz
# mariscos en Xalapa Veracruz

python scrappycat.py batch queries.txt --output output/xalapa_leads.csv
```

### City presets — full city in one command
```bash
python scrappycat.py city xalapa
python scrappycat.py city cdmx
python scrappycat.py city monterrey
```

---

## ⚙️ Options

| Flag | Default | Description |
|------|---------|-------------|
| `--limit` | 100 | Max results per query |
| `--depth` | 8 | Scroll depth (more = more results) |
| `--output` | output/leads.csv | Output file path |
| `--email` | on | Extract emails from websites |
| `--no-email` | — | Skip email extraction (faster) |

---

## 🗺️ City presets

| City | Queries included |
|------|-----------------|
| `xalapa` | restaurantes, cafeterías, mariscos, fondas, taquerías, bares, pizzerías |
| `cdmx` | restaurantes, cafeterías, bares, taquerías |
| `monterrey` | restaurantes, cafeterías, bares |

Want your city? Open a PR or an issue.

---

## 💡 Why ScrappyCat?

Most Google Maps scrapers either:
- Require Docker (slow on Apple Silicon)
- Cost money per search
- Break after 10 results

ScrappyCat runs **natively** on Mac (ARM64), Windows, and Linux. No Docker, no subscriptions, no BS.

---

## 🤝 Contributing

PRs welcome. Ideas:
- More city presets
- WhatsApp bulk sender integration
- Export to Notion / Airtable / Google Sheets
- Web UI

---

## 📄 License

MIT — use it, fork it, sell it.

---

Made with 🐱 by [@miladyxx333-lab](https://github.com/miladyxx333-lab)
