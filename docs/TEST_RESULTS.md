# Integration release test report — v0.2.0

Run in the release directory with `PYTHONPATH=src python -m unittest discover -s tests -q` (offline, no external credentials):

```text
Ran 132 tests
OK
```

Checked additional integration paths:

- `PYTHONPATH=src python -m radar.service --mode demo --database-url /tmp/memecoin_radar_demo.db`: local stored scan succeeded, emits 0 opportunity alerts.
- `node --check cloudflare/src/index.js`: JavaScript syntax check succeeded.
- Python source import / compile: passed.
- GitHub Actions YAML and Neon/Cloudflare *live* deployment: NOT validated here.
- Real Helius / GeckoTerminal from this runtime: NOT tested due to DNS/network restriction. Historical real-market logs provided by user verified that v0.1.9 parsed PumpSwap pool accounts and maintained HOLD_UNKNOWN, not that the v0.2.0 integrations have been live tested.

**External runtime restrictions:** the container attempted the public GeckoTerminal URL and could not resolve DNS. No user API key was sent to an external endpoint, stored in the code, or copied to this archive. Rotate exposed keys before deployment.

**Important:** unit tests and syntax checks do not establish scam detection accuracy, prediction quality, safe liquidity, sellability, or production-grade availability. Mandatory checks remain UNKNOWN, so opportunity alerts remain disabled.
