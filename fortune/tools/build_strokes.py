"""產生姓名學的筆畫表（fortune/xingming/strokes.tsv）— 資料來自 Unicode 官方的 Unihan 資料庫。

用法：python -m fortune.tools.build_strokes [Unihan.zip 路徑]
沒給路徑就從 unicode.org 下載最新版。只有更新 Unicode 版本時才需要重跑，產物已進 repo。

每一列：字、康熙部首號、部首以外的筆畫、總筆畫（台灣）、正體字（只有簡化字才有）
- kRSUnicode「170.8」＝ 部首 170（阜）＋ 其餘 8 畫；部首號後面帶 ' 的是簡化部首
- kTotalStrokes 有兩個值時，第一個是大陸、第二個是台灣，這裡取台灣
- kTraditionalVariant：簡化字對應的正體字（只收唯一對應的）
"""

from __future__ import annotations

import io
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

URL = "https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip"
OUT = Path(__file__).resolve().parents[1] / "xingming" / "strokes.tsv"
RANGES = [(0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF)]   # 擴充 A、基本區、相容區


def _in_range(cp: int) -> bool:
    return any(a <= cp <= b for a, b in RANGES)


def build(zip_bytes: bytes) -> tuple[list[str], str]:
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    rs: dict[int, str] = {}
    total: dict[int, str] = {}
    trad: dict[int, str] = {}
    version = ""
    for name in ("Unihan_IRGSources.txt", "Unihan_Variants.txt"):
        for line in z.read(name).decode("utf-8").splitlines():
            if line.startswith("# Unicode Version"):
                version = line[2:].strip()
            if not line.startswith("U+"):
                continue
            code, field, value = line.split("\t", 2)
            cp = int(code[2:], 16)
            if not _in_range(cp):
                continue
            if field == "kRSUnicode":
                rs[cp] = value.split()[0]
            elif field == "kTotalStrokes":
                total[cp] = value.split()[-1]
            elif field == "kTraditionalVariant":
                vs = [chr(int(v[2:], 16)) for v in value.split()]
                if len(vs) == 1 and vs[0] != chr(cp):
                    trad[cp] = vs[0]
    rows = []
    for cp in sorted(rs):
        m = re.fullmatch(r"(\d+)('*)\.(-?\d+)", rs[cp])
        if not m or cp not in total:
            continue
        radical = m.group(1) + ("'" if m.group(2) else "")
        rows.append("\t".join([chr(cp), radical, m.group(3), total[cp], trad.get(cp, "")]).rstrip("\t"))
    return rows, version


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    data = Path(argv[0]).read_bytes() if argv else urllib.request.urlopen(URL, timeout=60).read()
    rows, version = build(data)
    header = (f"# 姓名學筆畫表：由 fortune/tools/build_strokes.py 從 Unihan（{version}）產生，勿手改。\n"
              "# 資料來源 Unicode Character Database（Unihan）© Unicode, Inc.，依 Unicode License v3 使用：https://www.unicode.org/license.txt\n"
              "# 字\t康熙部首號\t其餘筆畫\t總筆畫(台灣)\t正體字(簡化字才有)\n")
    OUT.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"寫入 {OUT}：{len(rows)} 字（{version}）")


if __name__ == "__main__":
    main()
