# 05 · Empirical simulation — what an unprivileged caller can reach

Method: `eth_call` against **current Base mainnet state** with `from` set to an arbitrary unprivileged EOA
`0x00000000000000000000000000000000deadBeef` (holds no role, no balance, no approval anywhere). `eth_call`
executes the state-changing function against live state without committing, returning the exact revert reason or
success. Scripts: [`../tools/simulate.py`](../tools/simulate.py), [`../tools/simulate_mintpath.py`](../tools/simulate_mintpath.py).
Raw output: [`../data/simulation_results.txt`](../data/simulation_results.txt).

## Results

| Target · call | From attacker → | Meaning |
|---|---|---|
| `Nock.mint(attacker, 1e21)` | **REVERT** `Only inbox can mint` | Cannot mint out of thin air. |
| `Nock.updateInbox(attacker)` | **REVERT** `OwnableUnauthorizedAccount` (`0x118cdaa7`) | Cannot seize mint authority. |
| `Nock.burn(1e21, 0x..)` | **REVERT** `Insufficient balance` | Cannot burn tokens not held (burn itself is public by design). |
| `MessageInbox.submitDeposit(…, 3 forged sigs)` | **REVERT** `Invalid signature` | Forged sigs fail ECDSA recovery. |
| `MessageInbox.submitDeposit(…, 3 VALID non-node sigs)` | **REVERT** `Invalid Ethereum signatures` | **Well-formed** sigs from non-bridge keys fail the 3-of-5 **membership** count. This is the key proof: the mint gate is node-membership, not signature validity. |
| `MessageInbox.updateBridgeNode(0, attacker)` | **REVERT** `OwnableUnauthorizedAccount` | Cannot swap in an attacker signer. |
| `MessageInbox.setWithdrawalsEnabled(false)` | **REVERT** `OwnableUnauthorizedAccount` | Cannot brick withdrawals. |
| `MessageInbox.upgradeToAndCall(attacker, 0x)` | **REVERT** `OwnableUnauthorizedAccount` | Cannot replace mint logic. |
| `MessageInbox.notifyBurn()` (spoofed) | **REVERT** `Only Nock contract can notify burns` | Cannot spoof burn notifications. |
| `Safe.execTransaction(…, empty sigs)` | **REVERT** `execution reverted` (GS020-class) | Admin actions need the 3-of-5 quorum. |
| `Pool.skim(attacker)` | **REACHED** (no-op) | Confirms the pool is **live and not paused**; permissionless AMM housekeeping is open (expected). |

## Interpretation
- The entire **mint + admin surface is closed** to an unprivileged caller. Every guard documented in
  [`03_authorities.md`](03_authorities.md) and [`04_mint_path_analysis.md`](04_mint_path_analysis.md) holds
  against a live adversarial call.
- The **only** reachable state-changing actions for an arbitrary address are the by-design public ones: burning
  your own NOCK, and interacting with the (canonical, unpaused) Aerodrome pool.
- Therefore the attack surface is **not** an unprivileged on-chain caller. It is exactly the off-chain root of
  trust — the 3-of-5 keys and the bridge that decides what they sign ([`06_offchain_components.md`](06_offchain_components.md)).

> The simulations exercise the guards; they are not an exploit attempt and change no state.
