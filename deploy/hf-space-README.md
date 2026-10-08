---
title: Bazaar of Fates · 算命
emoji: 🔮
colorFrom: purple
colorTo: pink
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: 13 divination systems, one birth moment — charts + readings
---

# Bazaar of Fates · 算命

Thirteen traditional divination systems (西洋占星 · 八字 · 紫微斗數 · 梅花易數 · 六爻 · 小六壬 · 四柱推命 · 七政四餘 · 鐵板神數 · 奇門遁甲 · 大六壬 · 太乙神數 · Jyotiṣa) cast from one birth moment, with real astronomy and a rule-based facts digest. This Space runs the **mock reader** (no API key): every chart is exact; the prose reading is the deterministic facts digest.

Source & docs: https://github.com/ChiShengChen/bazaar-of-fates

**To deploy:** create a Docker Space, copy this file to its `README.md`, add the repo's `Dockerfile` and source (or point the Space at the GitHub repo), optionally set `LLM_BACKEND=anthropic` and `ANTHROPIC_API_KEY` as Space secrets for real readings.
