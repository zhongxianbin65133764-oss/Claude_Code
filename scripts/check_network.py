"""Network diagnostic — can this machine reach everything the bot needs?

Tests each endpoint the bot talks to and reports HTTP status +
round-trip time. Uses stdlib only so it works immediately after
`git clone`, before you've installed any dependencies.

Run:  python3 scripts/check_network.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

# (name, url, method, body, why_it_matters)
CHECKS = [
    ("Gamma  (market discovery)",
     "https://gamma-api.polymarket.com/markets?limit=1",
     "GET", None,
     "Needed in dry-run AND live. The bot can't find markets without it."),
    ("CLOB   (orderbook reads)",
     "https://clob.polymarket.com/markets?limit=1",
     "GET", None,
     "Needed in dry-run AND live. Reads bid/ask before any trade."),
    ("Coinbase candles (oracle)",
     "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400",
     "GET", None,
     "Used by USE_ORACLE=true for crypto-market verification. Can disable."),
    ("Polygon RPC (orders)",
     "https://polygon-rpc.com",
     "POST",
     '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}',
     "Live mode only. Used to sign and submit transactions."),
]


# ANSI colors (auto-disabled when piped)
def _supports_color() -> bool:
    return sys.stdout.isatty()


class C:
    if _supports_color():
        G = "\033[32m"; R = "\033[31m"; Y = "\033[33m"
        DIM = "\033[2m"; BOLD = "\033[1m"; RESET = "\033[0m"
    else:
        G = R = Y = DIM = BOLD = RESET = ""


def _request(method: str, url: str, body: str | None, timeout: float = 10.0):
    headers = {
        # Polymarket and several others block the default Python-urllib UA
        # outright. Pretend to be a normal browser request.
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                      "Version/17.0 Safari/605.1.15",
        "Accept": "application/json,*/*;q=0.5",
    }
    if method == "GET":
        req = urllib.request.Request(url, headers=headers)
    else:
        req = urllib.request.Request(
            url,
            data=(body or "").encode(),
            headers={**headers, "Content-Type": "application/json"},
            method=method,
        )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body_bytes = r.read(2048)
            return r.status, body_bytes, time.monotonic() - t0, None
    except urllib.error.HTTPError as e:
        return e.code, b"", time.monotonic() - t0, None
    except Exception as e:  # noqa: BLE001
        return None, b"", time.monotonic() - t0, str(e)


def _verdict(name: str, status: int | None, body: bytes, err: str | None) -> str:
    if status is None:
        if "Name or service not known" in (err or "") or "nodename" in (err or ""):
            return "dns-fail"
        if "timed out" in (err or "") or "timeout" in (err or "").lower():
            return "timeout"
        if "Connection refused" in (err or ""):
            return "refused"
        return "network-error"
    if 200 <= status < 300:
        # For Polygon RPC, even 200 might be a soft error; check body
        if "Polygon" in name and body:
            try:
                data = json.loads(body)
                if "result" in data:
                    return "ok"
                return "rpc-error"
            except (json.JSONDecodeError, ValueError):
                return "bad-response"
        return "ok"
    if status in (401, 403):
        return "geo-blocked"
    if status == 429:
        return "rate-limited"
    return f"http-{status}"


def main() -> int:
    print(f"{C.BOLD}Polymarket Arb Bot — network diagnostic{C.RESET}")
    print("=" * 64)
    print()

    results = []
    for name, url, method, body, _ in CHECKS:
        sys.stdout.write(f"  {name:<32} ")
        sys.stdout.flush()
        status, body_bytes, elapsed, err = _request(method, url, body)
        verdict = _verdict(name, status, body_bytes, err)
        if verdict == "ok":
            print(f"{C.G}OK{C.RESET}  {C.DIM}{int(elapsed * 1000)} ms{C.RESET}")
        elif verdict == "geo-blocked":
            print(f"{C.R}BLOCKED {status}{C.RESET}  {C.DIM}{int(elapsed * 1000)} ms{C.RESET}")
        elif verdict == "timeout":
            print(f"{C.R}TIMEOUT{C.RESET}  {C.DIM}{int(elapsed * 1000)} ms{C.RESET}")
        elif verdict == "dns-fail":
            print(f"{C.R}DNS-FAIL{C.RESET}")
        elif verdict == "rate-limited":
            print(f"{C.Y}RATE-LIMITED{C.RESET}  (retry later)")
        else:
            print(f"{C.R}{verdict}{C.RESET}  {C.DIM}{err or status}{C.RESET}")
        results.append((name, verdict, elapsed))

    print()
    print("=" * 64)
    print(f"{C.BOLD}Verdict{C.RESET}")
    print("-" * 64)

    gamma_ok = results[0][1] == "ok"
    clob_ok = results[1][1] == "ok"
    cb_ok = results[2][1] == "ok"
    rpc_ok = results[3][1] == "ok"

    if gamma_ok and clob_ok:
        if cb_ok:
            print(f"  {C.G}✓ Dry-run ready.{C.RESET} Markets, books, and crypto oracle all reachable.")
        else:
            print(f"  {C.Y}⚠ Dry-run partially ready.{C.RESET} Markets and books OK, but")
            print(f"    Coinbase is unreachable. Set {C.BOLD}USE_ORACLE=false{C.RESET} in .env")
            print(f"    or your crypto-market verifications will fail.")
        if rpc_ok:
            print(f"  {C.G}✓ Live mode network paths OK.{C.RESET}")
        else:
            print(f"  {C.Y}⚠ Live mode: Polygon RPC unreachable.{C.RESET}")
            print(f"    Only matters when DRY_RUN=false. Try POLYGON_RPC_URL=")
            print(f"    a paid provider (Alchemy / Infura) instead of polygon-rpc.com.")
    else:
        print(f"  {C.R}✗ DRY-RUN BLOCKED.{C.RESET} The bot cannot run from this network.")
        print()
        print(f"  Likely causes:")
        if not gamma_ok:
            print(f"    - Polymarket geo-blocks: {C.BOLD}CN, US, UK, FR, SG{C.RESET} and others")
        if any(r[1] == "dns-fail" for r in results):
            print(f"    - DNS not resolving — check your network connection")
        if any(r[1] == "timeout" for r in results):
            print(f"    - Slow / firewalled network — VPN may help")
        print()
        print(f"  Fixes:")
        print(f"    1. Connect a VPN with endpoint outside blocked regions")
        print(f"    2. Or run the bot on a VPS (DigitalOcean / Hetzner) in an allowed region")
        print(f"    3. If only Coinbase is blocked, set USE_ORACLE=false in .env")

    print()
    return 0 if (gamma_ok and clob_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
