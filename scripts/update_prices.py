#!/usr/bin/env python3
"""Update LIVE-DATA prices/fx/history in index.html from Yahoo Finance."""
import json, re, sys, urllib.request, datetime, zoneinfo

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

def yahoo(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    meta = data["chart"]["result"][0]["meta"]
    price = meta["regularMarketPrice"]
    prev = meta.get("chartPreviousClose") or meta.get("previousClose")
    chg = round((price - prev) / prev * 100, 2) if prev else None
    return price, chg

def main():
    path = "index.html"
    html = open(path, encoding="utf-8").read()
    m = re.search(r'(<script id="live-data" type="application/json">\s*)(\{.*?\})(\s*</script>)', html, re.S)
    live = json.loads(m.group(2))

    failed = []
    for t in list(live["prices"].keys()):
        # Yahoo symbol: HK tickers need 4-digit zero-padded prefix e.g. 0700.HK -> 0700.HK (already ok)
        try:
            p, chg = yahoo(t)
            live["prices"][t] = {"price": round(p, 4), "changePct": chg}
        except Exception as e:
            failed.append(f"{t}: {e}")
    for cur, sym in (("USD", "THB=X"), ("HKD", "HKDTHB=X")):
        try:
            p, _ = yahoo(sym)
            live["fx"][cur] = round(p, 4)
        except Exception as e:
            failed.append(f"{cur}: {e}")

    tz = zoneinfo.ZoneInfo("Asia/Bangkok")
    now = datetime.datetime.now(tz)
    today = now.strftime("%Y-%m-%d")
    months = ["ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.","มิ.ย.","ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."]
    live["updatedAt"] = f"{now.day} {months[now.month-1]} {now.year} {now.strftime('%H:%M')} น. (Yahoo Finance)"
    live["updatedAtMs"] = int(now.timestamp() * 1000)

    hist = live.setdefault("history", [])
    entry = {"d": today,
             "prices": {t: v["price"] for t, v in live["prices"].items()},
             "fx": dict(live["fx"])}
    hist[:] = [e for e in hist if e["d"] != today]
    hist.append(entry)
    hist.sort(key=lambda e: e["d"])
    if len(hist) > 400:
        hist[:] = [hist[0]] + hist[-399:]   # keep baseline + recent

    new_json = json.dumps(live, ensure_ascii=False, indent=1)
    html = html[:m.start(2)] + new_json + html[m.end(2):]
    open(path, "w", encoding="utf-8").write(html)
    print("updated", today, "| failed:", failed or "none")
    if len(failed) >= len(live["prices"]):
        sys.exit(1)

if __name__ == "__main__":
    main()
