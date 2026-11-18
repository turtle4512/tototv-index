"""抓 5 个片源的全部片名，算拼音首字母，出电视 App 用的首字母名单 index.txt.gz。

python3 crawl.py full   # 全量翻页（首次，约 2.5 万页）
python3 crawl.py inc    # 增量：只拉最近 48 小时更新的（每天跑）
python3 crawl.py index  # 不抓，只拿 titles.json 重出名单

名单每行「首字母\t片名\t几个源有」，按首字母排，同首字母里源多的在前；
多音字另出至多 3 个别的读法（源数记 0，排在正读后面），如 琅琊榜之风起长林 正读 LYBZFQZL、另有 LYBZFQCL。
"""
import itertools
import concurrent.futures as cf
import gzip
import json
import re
import sys
import time
import urllib.parse
import urllib.request

from pypinyin import Style, lazy_pinyin, pinyin

SITES = [
    "http://cj.ffzyapi.com/api.php/provide/vod",
    "https://ikunzyapi.com/api.php/provide/vod",
    "http://caiji.dyttzyapi.com/api.php/provide/vod/from/dyttm3u8/at/m3u8",
    "https://api.wujinapi.com/api.php/provide/vod",
    "https://api.guangsuapi.com/api.php/provide/vod",
]
ADULT = re.compile("伦理|三级|写真|里番|擦边|两性|热舞|福利")
SEASON = re.compile(r"\s*(第[0-9一二三四五六七八九十百]+[季部期]|season\s*\d+|s\d+)\s*$", re.I)
TITLES = "titles.json"  # {片名: 出现在几个源}


def get(api, params, tries=3):
    url = api + "?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "okhttp/5.0.0"})
            return json.loads(urllib.request.urlopen(req, timeout=15).read())
        except Exception:
            time.sleep(1 + i * 2)
    return None


def base(name):
    name = re.sub(r"\s+", " ", (name or "").strip())
    prev = None
    while prev != name:
        prev, name = name, SEASON.sub("", name).strip(" ：:-·")
    return name


def site_names(api, extra):
    first = get(api, {"ac": "list", "pg": 1, **extra})
    if not first:
        print("FAIL", api, file=sys.stderr)
        return set()
    pages = int(first.get("pagecount") or 1)
    names = set()

    def take(d):
        for v in (d or {}).get("list", []):
            if not ADULT.search(v.get("type_name") or ""):
                n = base(v.get("vod_name"))
                if n:
                    names.add(n)

    take(first)
    with cf.ThreadPoolExecutor(6) as ex:
        for i, d in enumerate(ex.map(lambda p: get(api, {"ac": "list", "pg": p, **extra}), range(2, pages + 1))):
            take(d)
            if i % 500 == 0:
                print(api[:30], i, "/", pages, len(names), flush=True)
    print("done", api[:30], pages, "pages", len(names), "names", flush=True)
    return names


def letter(part):
    for ch in part:
        if ch.isascii() and ch.isalnum():
            return ch.upper()
    return ""


def initials(name):
    return "".join(letter(p) for p in lazy_pinyin(name, style=Style.FIRST_LETTER, errors=lambda s: list(s)))


def variants(name, key, cap=3):
    """多音字的别的读法拼出来的首字母（正读除外，至多 cap 个）。"""
    opts = []
    for p in pinyin(name, style=Style.FIRST_LETTER, heteronym=True, errors=lambda s: list(s)):
        letters = list(dict.fromkeys(filter(None, (letter(x) for x in p))))
        if letters:
            opts.append(letters)
    out = []
    for combo in itertools.product(*opts):
        v = "".join(combo)
        if v != key and v not in out:
            out.append(v)
            if len(out) >= cap:
                break
    return out


def main(mode):
    try:
        titles = json.load(open(TITLES, encoding="utf-8"))
    except FileNotFoundError:
        titles = {}
    if mode != "index":
        extra = {} if mode == "full" else {"h": 48}
        for api in SITES:
            for n in site_names(api, extra):
                if mode == "full" or n not in titles:
                    titles[n] = titles.get(n, 0) + 1
        json.dump(titles, open(TITLES, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    rows = []
    for n, c in titles.items():
        key = initials(n)
        if len(key) < 2:
            continue
        rows.append((key, 0, -c, len(n), n, c))
        for v in variants(n, key):
            rows.append((v, 1, -c, len(n), n, 0))
    rows.sort()
    with gzip.open("index.txt.gz", "wt", encoding="utf-8", compresslevel=9) as f:
        for key, _, _, _, n, c in rows:
            f.write(f"{key}\t{n}\t{c}\n")
    print("titles", len(titles), "rows", len(rows))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "inc")
