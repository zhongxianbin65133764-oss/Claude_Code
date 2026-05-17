"""Offline tests for the network diagnostic script's classifier logic."""
from __future__ import annotations

import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "check_network", os.path.join(ROOT, "scripts", "check_network.py")
)
check_network = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_network)


def test_verdict_ok_for_2xx():
    assert check_network._verdict("Gamma", 200, b"[]", None) == "ok"


def test_verdict_geo_blocked_for_403():
    assert check_network._verdict("Gamma", 403, b"", None) == "geo-blocked"


def test_verdict_rate_limited_for_429():
    assert check_network._verdict("CLOB", 429, b"", None) == "rate-limited"


def test_verdict_dns_fail():
    err = "[Errno -2] Name or service not known"
    assert check_network._verdict("Gamma", None, b"", err) == "dns-fail"


def test_verdict_timeout():
    assert check_network._verdict("Gamma", None, b"", "timed out") == "timeout"


def test_verdict_connection_refused():
    assert check_network._verdict("RPC", None, b"", "Connection refused") == "refused"


def test_verdict_polygon_rpc_2xx_with_valid_result_is_ok():
    body = b'{"jsonrpc":"2.0","id":1,"result":"0xabc123"}'
    assert check_network._verdict("Polygon RPC", 200, body, None) == "ok"


def test_verdict_polygon_rpc_2xx_without_result_is_rpc_error():
    body = b'{"jsonrpc":"2.0","id":1,"error":{"code":-32000}}'
    assert check_network._verdict("Polygon RPC", 200, body, None) == "rpc-error"
