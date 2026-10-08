# Launch kit · 發布素材

Copy-paste listings for the MCP / skill directories, plus the Space and PyPI steps. Keep every channel on the same day.

## One-liners

- **EN**: Bazaar of Fates — 13 traditional divination systems (Western astrology, BaZi, Zi Wei Dou Shu, I Ching, Liu Yao, Jyotiṣa, Qi Men, Da Liu Ren…) cast from one birth moment with real astronomy, cross-validated against Swiss Ephemeris and iztro. Question-oriented readings, cross-tradition synthesis, date picking. CLI, API, web, MCP server. MIT.
- **中文**：Bazaar of Fates · 算命 — 一個生辰、十三套命理（西洋占星、八字、紫微、梅花、六爻、小六壬、四柱推命、七政四餘、鐵板、奇門、六壬、太乙、Jyotiṣa），精確節氣與天文曆，對 Swiss Ephemeris 與 iztro 交叉驗證；問題導向解讀、跨門派綜合會診、擇日。CLI／API／網頁／MCP server，MIT。

## MCP Registry (`server.json` sketch)

```json
{
  "name": "io.github.ChiShengChen/bazaar-of-fates",
  "description": "13 divination systems (Western astrology, BaZi, Zi Wei Dou Shu, I Ching, Jyotisha, Qi Men, Da Liu Ren...) from one birth moment: deterministic charts, question-oriented readings, cross-tradition synthesis, date picking.",
  "repository": {"url": "https://github.com/ChiShengChen/bazaar-of-fates", "source": "github"},
  "version": "0.2.0",
  "packages": [{"registry_type": "pypi", "identifier": "bazaar-of-fates", "version": "0.2.0", "transport": {"type": "stdio"}, "runtime_hint": "uvx", "package_arguments": [{"type": "positional", "value": "bazaar-mcp"}]}]
}
```

Tools: `list_systems`, `geo_lookup`, `cast`, `reading`, `synthesis`, `zeri`, `day`, `synastry`. Install: `pip install "bazaar-of-fates[mcp]"` → command `bazaar-mcp`.

## mcp.so / Smithery / awesome-mcp-servers entry

**Bazaar of Fates** — `bazaar-mcp` · Python · MIT
Cast 13 traditional divination charts (西洋占星 · 八字 · 紫微斗數 · 梅花易數 · 六爻 · 小六壬 · 四柱推命 · 七政四餘 · 鐵板神數 · 奇門遁甲 · 大六壬 · 太乙神數 · Jyotiṣa) from a birth date/time/place with real ephemeris positions and minute-exact solar terms. Every tool returns an audit trail of facts; `synthesis` puts all systems on one question with per-tradition verdicts; `zeri` scores dates for weddings, openings, moves, contracts, surgery; `day` gives today's outlook with 12 時辰. Cross-validated in tests against Swiss Ephemeris, iztro, kinliuren, kinqimen, lunar-python.
`{"mcpServers": {"bazaar-of-fates": {"command": "bazaar-mcp"}}}`

awesome-mcp-servers line:
`- [ChiShengChen/bazaar-of-fates](https://github.com/ChiShengChen/bazaar-of-fates) 🐍 🏠 - 13 traditional divination systems (Western astrology, BaZi, Zi Wei Dou Shu, I Ching, Jyotisha, Qi Men, Da Liu Ren…) with real astronomy: charts, question-oriented synthesis, date picking.`

## Claude Code skill

`skills/bazaar-of-fates/SKILL.md` — copy into `~/.claude/skills/` or a project's `.claude/skills/`. Submit the same folder to the skills directories (skills.sh, skillselion) with the one-liner above.

## Hugging Face Space (free, no API key)

1. New Space → Docker → name `bazaar-of-fates`.
2. Push this repo (or `git remote add hf …`): the `Dockerfile` serves the API and the static page on port 7860. Replace the Space's `README.md` with `deploy/hf-space-README.md`.
3. Optional secrets: `LLM_BACKEND=anthropic`, `ANTHROPIC_API_KEY` for real readings.
4. Put the Space link at the top of the README: `👉 線上試玩 / Try it online`.

## PyPI

```bash
pip install build twine && python -m build && twine upload dist/*
uvx bazaar-of-fates bazi 1990-06-15 14:30 --place 台北     # after publishing
```

## Assets

- `python scripts/record_demo.py gif` → `docs/img/demo.gif` (hero GIF for the README's first screen).
- `python scripts/record_demo.py social` → `docs/img/social-preview.png` (GitHub → Settings → Social preview, 1280×640).

## Channels (same 24–48 h)

- EN: Show HN (「Show HN: 13 traditional divination systems as one deterministic engine — real astronomy, every chart auditable」), r/Python, r/SideProject, r/astrology, r/vedicastrology, r/iching. Tool-introduction tone; no accuracy claims.
- 中文: V2EX 分享創造, HelloGitHub (issue 模板：亮點 + 痛點 + 截圖), 阮一峰週刊 (issue 投稿), 掘金, linux.do.
- 台灣: Threads, 小紅書, 命理 FB 社團 — 主圖用盤面截圖與 GIF。
- Product Hunt a week later as the second wave. Never buy or swap stars.
