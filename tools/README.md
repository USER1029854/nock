# tools — reproducibility

Standalone Python (no external services beyond public Base RPC + block explorers). Run from this directory.

| Script | What it does |
|---|---|
| `rpc.py` | Minimal Base RPC helper: `eth_call`/storage/getCode, ABI encode/decode, self-contained keccak256 (verified against known vectors), and `try_call` (captures revert reasons). Imported by the others. |
| `simulate.py` | Unprivileged-caller reachability probes from `0x…deadBeef` against **live** state (mint/admin/burn/upgrade/notifyBurn/Safe). Prints REVERT reason vs REACHED. → [`docs/05`](../docs/05_simulation_results.md) |
| `simulate_mintpath.py` | Reconstructs `MessageInbox`'s deposit `messageHash` and signs it with 3 throwaway (non-node) keys to prove the mint gate is 3-of-5 **membership**, not signature validity. (Needs `pip install eth-account`.) |
| `evidence.py` | Reads V2Locker instance state and Nock `InboxUpdated` history (premine check). |
| `scan_history.py` | Full-range `getLogs` scan for `InboxUpdated`/`Upgraded` (authority-change events) with explicit error accounting. |
| `extract.py` | Turns an Etherscan `getsourcecode` JSON into a real file tree (used to build `src/`). |

### Notes
- RPC endpoints are public (`mainnet.base.org`, `publicnode`, `drpc`). Some public nodes cap `eth_getLogs`
  block-range; the full-history event counts in [`docs/07`](../docs/07_deposit_history_evidence.md) were
  confirmed via Blockscout's server-side `getLogs` (Etherscan-compatible endpoint).
- All simulations are `eth_call` only — they execute against current state and commit nothing.
- Live values (reserves, nonce, block) drift with new blocks; re-running reproduces the same **structure**
  (guards, authorities, history), with updated numbers.
