# Stage 2 — PumpSwap Pool Layout v0.1.8

Reads PumpSwap account binary data from the **existing third RPC batch**, checks Anchor Pool discriminator and decodes pair/mint/vault addresses using the official PumpSwap IDL. Explicitly verifies that the pool's base mint equals the discovered coin mint; mismatches are reported as data-quality issues, not as scam claims.

No new RPC calls, no trading, no new Opportunity Alerts. Contract checks remain unchanged. **Liquidity ownership, LP burning/locking, actual vault account state and W01/W02 remain UNKNOWN**. The new status `POOL_LAYOUT_VERIFIED_VAULTS_UNCHECKED` is identity-level verification only.

## Windows update

```powershell
Expand-Archive "$env:USERPROFILE\Downloads\MemeCoin_AI_Radar_Stage2_PumpSwap_Pool_Layout_v0.1.8.zip" -DestinationPath . -Force
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -m radar --mode live --rpc-check --holder-check --owner-check --pool-check --max-candidates 1
```

Requires v0.1.7 already installed. Do not include `.env`, Helius RPC URL or any secret in a public repository.

Source: https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump_amm.json
