# Family & Society News Agent — API Guide (for Frontend)

REST API for the Family & Society news agent. It has two families of endpoints:

1. **News listing** (`GET /news/...`) — fast, returns a JSON list of articles. No AI, no PDF. **~2 seconds.**
2. **AI reports** (`POST /reports/...`) — runs the LLM pipeline and produces a PDF. **Slow: 1–6 minutes.**

---

## 1. Running the server (backend)

From the `quality_bot` directory:

```bash
pip install -r requirements.txt
python -m uvicorn agent.api:app --host 0.0.0.0 --port 8010
```

- **Base URL:** `http://127.0.0.1:8010`
- **Interactive docs (Swagger):** `http://127.0.0.1:8010/docs`
- **CORS:** enabled for all origins in development, so you can call it directly from the browser.

---

## 2. Quick reference

| Method | Endpoint | Speed | Returns |
|--------|----------|-------|---------|
| `GET`  | `/health` | instant | Service + LLM status |
| `GET`  | `/news/daily` | ~2 s | List of articles (last 1 day) |
| `GET`  | `/news/weekly` | ~2 s | List of articles (last 7 days) |
| `GET`  | `/news/monthly` | ~2 s | List of articles (last 30 days) |
| `POST` | `/reports/daily` | 1–2 min | AI daily report + PDF |
| `POST` | `/reports/weekly` | 2–4 min | AI weekly report + PDF |
| `POST` | `/reports/monthly` | 2–4 min | AI monthly report + PDF |
| `POST` | `/reports/magazine` | 3–6 min | AI magazine + PDF |

> ⚠️ The `POST /reports/*` calls are long-running. Set your HTTP client timeout to **at least 10 minutes** (600000 ms) and show a loading state in the UI.

---

## 3. Health check

```
GET /health
```

**Response**
```json
{
  "status": "ok",
  "llm": { "bedrock": true, "azure": false },
  "model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
}
```

---

## 4. News listing endpoints (fast)

```
GET /news/daily
GET /news/weekly
GET /news/monthly
```

**Query parameters (all optional)**

| Param | Type | Default (daily / weekly / monthly) | Description |
|-------|------|-----------------------------------|-------------|
| `days` | int | `1` / `7` / `30` | Recency window in days (1–365) |
| `category` | string | none | Filter by category (see list below) |
| `limit` | int | `50` / `100` / `150` | Max articles to return (1–200) |

**Categories** (Arabic values — pass URL-encoded):
`الأسرة والطفولة`, `الصحة والرفاهية`, `المجتمع والقطاع غير الربحي`, `الإحصاء والدراسات`, `أخبار عامة`

**Response shape**
```json
{
  "period": "weekly",
  "days": 7,
  "category": null,
  "count": 5,
  "articles": [
    {
      "title": "مجلس شؤون الأسرة يطلق مبادرة لدعم الأسر المنتجة",
      "source": "مجلس شؤون الأسرة (@FAC_SA)",
      "url": "https://x.com/FAC_SA/status/...",
      "published_at": "2026-05-17T00:00:00Z",
      "description": "نص وصفي قصير ...",
      "image": null
    }
  ]
}
```

**Article object fields**

| Field | Type | Notes |
|-------|------|-------|
| `title` | string | Headline (Arabic) |
| `source` | string | e.g. `مجلس شؤون الأسرة (@FAC_SA)`, `الأمم المتحدة`, `Our World in Data` |
| `url` | string | Link to the original article |
| `published_at` | string \| null | ISO 8601 date |
| `description` | string \| null | Short summary |
| `image` | string \| null | Image URL if available |

**Examples**
```bash
curl "http://127.0.0.1:8010/news/daily"
curl "http://127.0.0.1:8010/news/weekly?limit=10"
curl "http://127.0.0.1:8010/news/monthly?category=الصحة والرفاهية"
```

---

## 5. AI report endpoints (slow, produce PDF)

```
POST /reports/daily
POST /reports/weekly
POST /reports/monthly
POST /reports/magazine
```

### Request body (optional — you can send none)

```jsonc
// /reports/daily
{ "category": "الصحة والرفاهية", "keywords": null }

// /reports/weekly, /reports/monthly, /reports/magazine
{ "keywords": null }
```

If you send a body, set header `Content-Type: application/json`. Sending **no body** is fine.

### `format` query parameter — controls the response

```
POST /reports/daily?format=file   (default)
POST /reports/daily?format=pdf
POST /reports/daily?format=json
```

| `format` | Response | Best for |
|----------|----------|----------|
| **`file`** (default) | JSON containing a `download_url` and `pdf_path` | Show a "Download / View PDF" link |
| `pdf` | The raw PDF binary (`application/pdf`) | Trigger a direct file download / embed |
| `json` | The generated text content, no PDF kept | Render the report text in the UI |

### Response — `format=file` (recommended for frontend)
```json
{
  "status": "ok",
  "report_type": "monthly",
  "time_period": "monthly",
  "article_count": 10,
  "enhanced_count": 10,
  "kind": "combined",
  "pdf_path": "C:\\...\\quality_bot\\generated\\Family_Monthly_Report_20260616_120000.pdf",
  "download_url": "http://127.0.0.1:8010/files/Family_Monthly_Report_20260616_120000.pdf"
}
```
→ Use `download_url` directly in an `<a href>` or `<iframe>` to view/download the PDF.

### Response — `format=json`
```json
{
  "report_type": "daily",
  "time_period": null,
  "enhanced_count": 20,
  "article_count": 20,
  "blog_content": "# التقرير اليومي للأسرة والمجتمع\n\n## نظرة سريعة\n...",
  "combined_blog": null,
  "magazine_data": null,
  "outputs": [{ "kind": "daily" }]
}
```

Which content field is populated depends on the endpoint:

| Endpoint | Populated field | Type |
|----------|-----------------|------|
| `/reports/daily` | `blog_content` | Markdown string (Arabic) |
| `/reports/weekly`, `/reports/monthly` | `combined_blog` | Markdown string (Arabic) |
| `/reports/magazine` | `magazine_data` | Structured JSON (see below) |

**`magazine_data` structure**
```jsonc
{
  "title": "مجلة الأسرة والمجتمع: ...",
  "subtitle": "...",
  "date": "June 2026",
  "highlights": [{ "title": "...", "description": "..." }],
  "editors_note": "...",
  "articles": [
    {
      "category": "الأسرة والطفولة",
      "title": "...",
      "location": "مكة المكرمة",
      "lead": "...",
      "content": "<p>محتوى HTML ...</p>",
      "source": "...",
      "score": "8",
      "image_url": "https://..."
    }
  ]
}
```

---

## 6. Frontend code examples (JavaScript `fetch`)

### News listing
```js
const res = await fetch("http://127.0.0.1:8010/news/weekly?limit=10");
const data = await res.json();
data.articles.forEach(a => console.log(a.title, a.url));
```

### AI report → get a PDF link (recommended)
```js
// Long request — show a spinner. Default format=file returns a download_url.
const res = await fetch("http://127.0.0.1:8010/reports/monthly", { method: "POST" });
const data = await res.json();
window.open(data.download_url, "_blank"); // open/view the PDF
```

### AI report → get the text to render in the UI
```js
const res = await fetch("http://127.0.0.1:8010/reports/daily?format=json", {
  method: "POST",
});
const data = await res.json();
renderMarkdown(data.blog_content); // e.g. with a markdown renderer (RTL/Arabic)
```

### Daily report with a category
```js
const res = await fetch("http://127.0.0.1:8010/reports/daily", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ category: "الصحة والرفاهية" }),
});
const data = await res.json();
```

### Download the raw PDF binary
```js
const res = await fetch("http://127.0.0.1:8010/reports/weekly?format=pdf", {
  method: "POST",
});
const blob = await res.blob();
const url = URL.createObjectURL(blob);
window.open(url); // or set as <a download> href
```

---

## 7. Errors

Errors use standard HTTP status codes with a JSON `detail` field.

```json
{ "detail": "لم يتم العثور على أخبار كافية عن الأسرة والمجتمع." }
```

| Status | Meaning |
|--------|---------|
| `200` | Success |
| `422` | Invalid request (bad `format`, wrong body type, out-of-range query) |
| `502` | Pipeline failed (no articles, LLM error, PDF render failed) |

---

## 8. Notes for the frontend

- **All text content is Arabic** → render with `dir="rtl"`.
- The report text (`blog_content` / `combined_blog`) is **Markdown** → use a markdown renderer that supports RTL.
- `magazine_data.articles[].content` is **HTML** → render as HTML.
- **Long requests:** `POST /reports/*` can take minutes. Use a generous timeout and a loading UI; consider letting the user kick it off and poll, or just await with a spinner.
- For production, change CORS `allow_origins` in `agent/api.py` from `"*"` to your real frontend domain.
- Generated PDFs are saved under `quality_bot/generated/` and served at `/files/<name>.pdf`.
