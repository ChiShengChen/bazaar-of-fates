---
name: bazaar-of-fates
description: Cast 13 traditional divination charts (西洋占星, 八字, 紫微斗數, 梅花易數, 六爻, 小六壬, 四柱推命, 七政四餘, 鐵板神數, 奇門遁甲, 大六壬, 太乙神數, Jyotiṣa) from a birth moment with real astronomy; answer one question across all systems (synthesis), pick dates (擇日), today's outlook. Use when the user asks for a natal chart, 命盤, 八字, 紫微, horoscope, 排盤, 合盤, 擇日, 流年, or a fortune reading.
---

# Bazaar of Fates · 算命

Deterministic charts first, interpretation second. Every tool returns a `reasoning_chain` (the audit trail) and `readings` (named facts); read FROM those, never invent chart elements.

## Setup

```bash
pip install "bazaar-of-fates[mcp]"       # CLI `bazaar` + MCP server `bazaar-mcp`
```

MCP (Claude Desktop / Claude Code / Cursor): `{"mcpServers": {"bazaar-of-fates": {"command": "bazaar-mcp"}}}`
No MCP? Use the CLI with `--json`:

```bash
bazaar bazi 1990-06-15 14:30 --place 台北 --gender female --json
bazaar synthesis 1990-06-15 14:30 --gender female --ask "明年事業" --json
bazaar zeri 1990-06-15 14:30 --purpose wedding --from 2026-11-01 --to 2026-12-31 --json
```

## Workflow

1. Collect birth date, time (if unknown, say so — ascendant/時柱 default to noon), gender, place. `geo_lookup` fills lat/lon/tz (Taiwan historical DST handled).
2. For one tradition: `cast` (facts) or `reading` (facts + prose; pass the user's question as `focus`, and `lang`).
3. For "what do the systems say about X": `synthesis` — show the per-system verdicts and reasons as a table, then explain agreements and conflicts in each tradition's own terms.
4. For "when should I…": `zeri` with the purpose; present the top days with their 吉時 and 吉方 and the hard-avoid days (沖日柱, 歲破).
5. For anything about love / romance / marriage (何時有緣, 合不合, 復合, 該不該分開, 婚姻, 第三者): `love` — pass gender (男命財星為妻、女命官殺為夫) and the partner's birth for 合婚. Present `timing.years` as a ranked list of 桃花年／婚緣年 with their reasons, `natal` as how this person loves, and `match` as the biggest + and − terms; never pronounce fate or decide a breakup for them.
6. Always keep the disclaimer: cultural / educational / entertainment; not a basis for medical, financial or legal decisions.

## Reading the payloads

- 八字: `chart.pillars[*]` (stem_god, hidden, nayin, kong_wang, shensha), `chart.strength` (label, yongshen, favourable, avoid, pattern, lines), `chart.dayun[*].liunian[*]`.
- 紫微: `chart.palaces[*]` (stars with `(祿/權/科/忌)` tags, brightness, adjective_stars, changsheng, boshi), `chart.luck.daxian[*]`.
- 六爻: `chart.hexagram.lines[*]` (relative, god, notes, shi/ying/moving/hidden), `changed`.
- 奇門: `chart.palaces[*]` (god · star · gate · sky_stem/earth_stem), `zhifu`, `zhishi`. 六壬: `courses`, `transmissions`, generals.
- Western / Jyotiṣa: `chart.planets|grahas` with house/bhava, `ascendant.houses`, `aspects_detail`.
