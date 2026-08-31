# ADR-0007: Autonomous Daily AI Briefing Pipeline

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-08-24
* **Authors**: Thang Hoang & Antigravity

---

## 1. Context & Problem Statement
We run multiple isolated microservices (VietCalendar astronomical API, Memos journal, VictoriaMetrics telemetry, and local AI runtimes). We wanted an automated, unified morning intelligence briefing without third-party SaaS tools.

---

## 2. Decision
1. **Scheduled Kubernetes CronJob (`daily-ai-briefing`)**:
   * Deployed via the Master Helm Chart (`charts/vinhthang-fleet/templates/daily-briefing-cronjob.yaml`).
   * Scheduled at `0 0 * * *` (00:00 UTC / **07:00 AM Indochina Time** / 09:00 AM Tokyo Time daily).
2. **Multi-Service Data Aggregation**:
   * **VietCalendar**: Fetches real-time solar & lunar dates, Can Chi, Hoàng Đạo auspicious hours, and upcoming Vietnamese holidays.
   * **Fleet Telemetry**: Gathers node memory headroom, container health, and SSL countdowns.
   * **AI Curation**: Curates 3 high-impact tech and architecture insights.
3. **Delivery**:
   * Formats into clean Markdown tagged `#DailyBriefing #VietCalendar #AI #Memos` and delivers directly into Memos (`memos.vinhthang.dev`).

---

## 3. Consequences
### Positive:
* Autonomous morning intelligence delivered automatically every day.
* Connects VietCalendar, Memos, and fleet telemetry into a cohesive user experience.
* Zero resource overhead (< 20 MB RAM during ephemeral execution).

### Negative / Trade-offs:
* Dependent on VietCalendar API availability for lunar holiday data (handled via fallback defaults).
