"""東方奇幻 theme for the Space — 夜墨 (ink night) chrome, 宣紙 (rice-paper) chart sheets, 金 / 硃砂 accents."""

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@400;600;700;900&family=Cormorant+Garamond:wght@500;600;700&display=swap');
:root{--ink:#0b0a14;--ink2:#15122a;--gold:#d4af37;--gold2:#f1d27a;--cinnabar:#b4302b;--paper:#f3e9d2;--paper2:#e9dcc0;--inkline:#3a2f1e;--mist:rgba(241,210,122,.14)}
body, .gradio-container{background:
  radial-gradient(1px 1px at 20% 30%, rgba(255,255,255,.55) 50%, transparent 51%),
  radial-gradient(1px 1px at 70% 15%, rgba(255,255,255,.45) 50%, transparent 51%),
  radial-gradient(1.5px 1.5px at 40% 80%, rgba(255,255,255,.4) 50%, transparent 51%),
  radial-gradient(1px 1px at 85% 60%, rgba(255,255,255,.5) 50%, transparent 51%),
  radial-gradient(1px 1px at 10% 70%, rgba(255,255,255,.35) 50%, transparent 51%),
  radial-gradient(ellipse at 50% -10%, #2a1f4a 0%, #15122a 45%, #0b0a14 100%) !important;
  color:#e8dcc0 !important; font-family:'Noto Serif TC','Songti TC','PingFang TC',serif !important}
.gradio-container{max-width:1180px !important; margin:0 auto !important}
.gradio-container *{font-family:'Noto Serif TC','Songti TC',serif}
.gradio-container code, .gradio-container pre{font-family:ui-monospace,Menlo,monospace}
.gradio-container .block, .gradio-container .form, .gradio-container .tabitem, .gradio-container .gr-box, .gradio-container .gr-panel{
  background:rgba(21,18,42,.72) !important; border:1px solid rgba(212,175,55,.35) !important; border-radius:14px !important; box-shadow:0 0 0 1px rgba(0,0,0,.4), 0 10px 40px rgba(0,0,0,.35) !important}
.gradio-container .block.padded{padding:14px !important}
.gradio-container label span, .gradio-container .label-wrap span, .gradio-container span.svelte-1gfkn6j{color:var(--gold2) !important; letter-spacing:.06em; font-weight:600}
.gradio-container input:not([type=checkbox]):not([type=radio]), .gradio-container textarea, .gradio-container select, .gradio-container .wrap-inner, .gradio-container .secondary-wrap{
  background:#0f0d1d !important; color:#efe4c8 !important; border:1px solid rgba(212,175,55,.35) !important; border-radius:10px !important}
.gradio-container input:focus, .gradio-container textarea:focus{border-color:var(--gold) !important; box-shadow:0 0 0 3px var(--mist) !important}
.gradio-container button.primary, .gradio-container .primary{background:linear-gradient(135deg,#7a1f1b 0%,#b4302b 55%,#d4af37 140%) !important; color:#fff5dc !important;
  border:1px solid rgba(241,210,122,.6) !important; font-weight:700 !important; letter-spacing:.2em; font-size:18px !important; border-radius:999px !important; box-shadow:0 6px 24px rgba(180,48,43,.35), inset 0 1px 0 rgba(255,255,255,.2) !important}
.gradio-container button.secondary{background:#1b1733 !important; color:var(--gold2) !important; border:1px solid rgba(212,175,55,.45) !important; border-radius:999px !important}
.gradio-container .tabs > .tab-nav{border-bottom:1px solid rgba(212,175,55,.35) !important}
.gradio-container .tab-nav button{color:#b9ab8a !important; font-size:15px !important; letter-spacing:.1em}
.gradio-container .tab-nav button.selected{color:var(--gold2) !important; border-bottom:2px solid var(--gold) !important}
.gradio-container .prose, .gradio-container .md, .gradio-container .prose p, .gradio-container .prose li{color:#e8dcc0 !important; font-size:15px; line-height:1.85}
.gradio-container .prose h1, .gradio-container .prose h2, .gradio-container .prose h3{color:var(--gold2) !important; letter-spacing:.08em}
.gradio-container .prose a{color:#f1d27a !important; text-decoration:underline dotted}
.gradio-container .prose strong{color:#fff3cf}
.gradio-container table.svelte-1ghsmn6, .gradio-container .table-wrap{background:transparent !important}
.gradio-container thead th{background:#1b1733 !important; color:var(--gold2) !important}
.gradio-container tbody td{background:rgba(21,18,42,.5) !important; color:#efe4c8 !important; border-color:rgba(212,175,55,.2) !important}
.gradio-container .accordion, .gradio-container .label-wrap{color:var(--gold2) !important}
.gradio-container input[type=checkbox]{accent-color:var(--cinnabar); width:18px; height:18px; background:#0f0d1d; border:1px solid var(--gold) !important; border-radius:4px}
.paper .v-fav{color:#2f6b2f; font-weight:900} .paper .v-neu{color:#7a6a4e; font-weight:700} .paper .v-unf{color:#b4302b; font-weight:900}
.paper tr.conflict td{background:rgba(180,48,43,.07) !important}
.paper .star{color:#b8892b; letter-spacing:-1px; white-space:nowrap}
.paper td.nw{white-space:nowrap}
.gradio-container span[data-testid="block-info"], .gradio-container .block > label > span, .gradio-container label > span.svelte-1b6s6s{color:var(--gold2) !important}
.gradio-container .wrap-inner, .gradio-container .secondary-wrap{border:none !important; background:transparent !important; box-shadow:none !important}
.gradio-container .dropdown .wrap, .gradio-container .wrap.svelte-1hfxrpf{background:#0f0d1d !important; border:1px solid rgba(212,175,55,.35) !important; border-radius:10px !important}
.gradio-container .tab-nav button, .gradio-container button[role=tab]{color:#d7c9a3 !important; background:transparent !important}
.gradio-container button[role=tab][aria-selected=true]{color:var(--gold2) !important; border-bottom:2px solid var(--gold) !important}
.gradio-container .dropdown, .gradio-container .wrap, .gradio-container .wrap-inner, .gradio-container .secondary-wrap, .gradio-container .dropdown-arrow{background:#0f0d1d !important; color:#efe4c8 !important}
.gradio-container .wrap input, .gradio-container .wrap-inner input{background:transparent !important; border:none !important}
.gradio-container ul.options, .gradio-container .options{background:#15122a !important; color:#efe4c8 !important; border:1px solid rgba(212,175,55,.35) !important}
.gradio-container .options .item:hover, .gradio-container .options .item.selected{background:rgba(212,175,55,.18) !important}
.gradio-container .paper table, .gradio-container .paper thead th, .gradio-container .paper tbody td, .gradio-container .paper tr{background:transparent !important; color:#1f1a12 !important; border-color:rgba(120,90,30,.35) !important}
.gradio-container .paper thead th{color:#6b5a3e !important}
.gradio-container .paper td:first-child, .gradio-container .paper .muted{color:#7a6a4e !important}
.hero code{color:#f1d27a; background:rgba(241,210,122,.08); padding:1px 6px; border-radius:4px; font-size:13px}
.gradio-container footer{display:none !important}
/* hero */
.hero{text-align:center; padding:26px 10px 6px}
.hero .title{font-family:'Cormorant Garamond','Noto Serif TC',serif; font-size:52px; font-weight:700; letter-spacing:.08em; line-height:1.1;
  background:linear-gradient(180deg,#fff3cf 0%,#f1d27a 45%,#b8892b 100%); -webkit-background-clip:text; background-clip:text; color:transparent; text-shadow:0 0 30px rgba(241,210,122,.15)}
.hero .title span{font-family:'Noto Serif TC',serif; font-weight:900; background:linear-gradient(180deg,#fff3cf 0%,#f1d27a 45%,#b8892b 100%); -webkit-background-clip:text; background-clip:text; color:transparent; -webkit-text-fill-color:transparent}
.hero .orn{color:var(--gold); letter-spacing:.6em; font-size:14px; margin:6px 0 2px; opacity:.9}
.hero .sub{color:#c9b98f; font-size:14px; letter-spacing:.12em; margin-top:8px}
.hero .sub a{color:#f1d27a}
.hero .seal{display:inline-block; border:2px solid var(--cinnabar); color:var(--cinnabar) !important; -webkit-text-fill-color:var(--cinnabar); background:rgba(180,48,43,.1); font-weight:900; padding:1px 6px; border-radius:4px; font-size:13px; margin-left:14px; vertical-align:middle; transform:rotate(-6deg); font-family:'Noto Serif TC',serif}
/* paper sheets (rendered HTML) */
.paper{background:linear-gradient(180deg,var(--paper) 0%,var(--paper2) 100%); color:#1f1a12; border:1px solid #b89a5a; border-radius:12px; padding:16px 18px; box-shadow:inset 0 0 60px rgba(120,90,30,.12), 0 8px 30px rgba(0,0,0,.35); position:relative}
.paper:before{content:""; position:absolute; inset:6px; border:1px solid rgba(120,90,30,.35); border-radius:8px; pointer-events:none}
.paper .title{font-weight:900; letter-spacing:.15em; color:#5b1f1b; font-size:18px; margin-bottom:8px}
.paper .title .seal{display:inline-block; border:2px solid var(--cinnabar); color:var(--cinnabar); padding:0 5px; border-radius:3px; font-size:12px; margin-left:8px; transform:rotate(-6deg)}
.paper table{border-collapse:collapse; width:100%}
.paper th,.paper td{border-bottom:1px solid rgba(120,90,30,.35); padding:5px 8px; text-align:center; vertical-align:top}
.paper th{color:#6b5a3e; font-weight:600; letter-spacing:.08em}
.paper td:first-child{text-align:left; color:#6b5a3e; white-space:nowrap}
.paper .big{font-size:26px; font-weight:900}
.paper .muted{color:#7a6a4e}
.paper .head{display:flex; flex-direction:column; gap:3px; margin:4px 0 12px; font-size:14px}
.paper .note{margin-top:5px; font-size:14px}
.paper .strip{display:flex; gap:5px; overflow-x:auto; margin:8px 0; padding-bottom:4px}
.paper .cell{flex:1 0 72px; border:1px solid #b89a5a; border-radius:8px; padding:5px 3px; text-align:center; font-size:12px; background:rgba(255,250,235,.6)}
.paper .cell.fav{background:#e3efd6; border-color:#5f8a3f} .paper .cell.unf{background:#f3d9d4; border-color:#b4302b} .paper .cell.now{outline:2px solid var(--cinnabar)}
.zw{display:grid; grid-template-columns:repeat(4,1fr); grid-template-rows:repeat(4,1fr); gap:5px; max-width:640px; aspect-ratio:1}
.zw .c{border:1px solid #b89a5a; border-radius:6px; padding:5px 7px; font-size:11.5px; display:flex; flex-direction:column; justify-content:space-between; overflow:hidden; background:rgba(255,250,235,.55)}
.zw .c.body{background:#f6e2c4; border-color:var(--cinnabar)}
.zw .maj{font-weight:900; font-size:14px; color:#1f1a12} .zw .min{color:#7a6a4e; font-size:10.5px} .zw .nm{color:#5b1f1b; margin-top:3px; font-weight:700}
.zw .ctr{grid-row:2/4; grid-column:2/4; border:1px solid #b89a5a; border-radius:8px; padding:10px; font-size:12.5px; text-align:center; display:flex; flex-direction:column; justify-content:center; gap:4px;
  background:radial-gradient(circle at 50% 50%, rgba(212,175,55,.18) 0%, transparent 70%), url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='46' fill='none' stroke='%23b89a5a' stroke-opacity='.35' stroke-width='1'/><circle cx='50' cy='50' r='30' fill='none' stroke='%23b89a5a' stroke-opacity='.25' stroke-width='.7'/><path d='M50 20a30 30 0 0 1 0 60a15 15 0 0 1 0-30a15 15 0 0 0 0-30z' fill='%23b89a5a' fill-opacity='.12'/></svg>") center/80% no-repeat}
.qm{display:grid; grid-template-columns:repeat(3,1fr); gap:5px; max-width:460px}
.qm .c{border:1px solid #b89a5a; border-radius:8px; padding:7px 9px; min-height:74px; font-size:13.5px; background:rgba(255,250,235,.55)}
.qm .c.good{border-color:#5f8a3f; background:#e8f0dc} .qm .c.bad{border-color:#b4302b; background:#f3d9d4} .qm .c.fu{outline:2px solid var(--cinnabar)}
.qm .t{display:flex; justify-content:space-between; font-size:11px; color:#5b1f1b} .qm .m{display:flex; justify-content:space-between}
.lr{display:grid; grid-template-columns:repeat(12,1fr); gap:3px}
.lr .c{border:1px solid #b89a5a; border-radius:6px; text-align:center; font-size:13px; padding:3px 0; background:rgba(255,250,235,.55)} .lr .g{font-size:10px; color:#5b1f1b}
.kv{display:grid; grid-template-columns:auto 1fr; gap:4px 14px; font-size:13.5px} .kv .k{color:#7a6a4e; white-space:nowrap}
"""

HERO = """
<div class="hero">
  <div class="orn">☰ ☱ ☲ ☳ &nbsp; 卜 · 命 · 相 &nbsp; ☴ ☵ ☶ ☷</div>
  <div class="title">Bazaar of Fates <span>· 算命</span><span class="seal">十三術</span></div>
  <div class="sub">一個生辰，十三套命理 — 西洋占星 · 八字 · 紫微斗數 · 梅花易數 · 六爻 · 小六壬 · 四柱推命 · 七政四餘 · 鐵板神數 · 奇門遁甲 · 大六壬 · 太乙神數 · Jyotiṣa</div>
  <div class="sub"><a href="https://github.com/ChiShengChen/bazaar-of-fates" target="_blank">GitHub</a> · <code>pip install bazaar-of-fates</code> · <a href="docs" target="_blank">API</a> · <a href="web/" target="_blank">靜態版</a></div>
</div>
"""
