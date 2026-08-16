# 07 · Historical evidence — no premine, one mint path, real usage

On-chain evidence about how the mint authority has **actually** been used over the token's ~8-month life. This
is the record that bounds the off-chain components in [`06`](06_offchain_components.md). Scripts:
[`../tools/evidence.py`](../tools/evidence.py), [`../tools/scan_history.py`](../tools/scan_history.py).

## 1. No premine — the authority-rewiring record is a single, benign step

The Nock **constructor set `inbox = address(0)`** (decoded from creation calldata). While `inbox == 0`, `mint`
is uncallable (`msg.sender` can never be `address(0)`). The full-history event scan (Blockscout
`getLogs`, server-side, full range) returns:

| Event | Count, all-time | The one occurrence |
|---|---|---|
| `Nock.InboxUpdated(old,new)` | **exactly 1** | block **39,685,415** (6 blocks / ~12s after deploy): `0x0` → **`0x2033…8021`** (the MessageInbox proxy) |
| `ERC1967 Upgraded(impl)` on the inbox proxy | **exactly 1** | block **39,685,413** (constructor): impl → **`0xcf69…be99`** (the current, verified `MessageInbox`) |

**Consequences (airtight):**
- `inbox` was `address(0)` from deploy until the single rewiring, then the MessageInbox proxy, and **never
  anything else** — so there was **never a temporary EOA inbox** to premine through.
- The proxy's implementation was set once (constructor) to the current impl and **never upgraded** — so **no
  prior mint logic ever existed**.
- Therefore **every NOCK in existence was minted by the exact `submitDeposit` (3-of-5) logic** in this repo.
  There is no premine, no alternate mint path, and no swapped-out implementation. This closes the
  upgradeability caveat completely.

Deployer (creation tx `0xfb4af9dd…`): EOA `0x4356D2C1B6f7238dcEE0a6E90c9B5B1717648555`. Holds no current role
(ownership is the Safe).

## 2. Deposit usage — real bridge, plausible amounts

From the `DepositProcessed` event log (`MessageInbox`):

| Metric | Value |
|---|---|
| Deposits processed (`lastDepositNonce`) | **462** |
| Events summed (Blockscout pagination) | 447 of ~462 (see note) |
| Sum of summed deposit amounts | ≈ **1,242,956,127 NOCK** |
| Live `totalSupply` | ≈ **1,315,153,008 NOCK** |
| Max single deposit | ≈ **52,343,788 NOCK** → recipient `0xE61894033Eec8CE33862F8c6B8C1aeC56FD386e8` |
| Distinct recipients (in sample) | **181** |
| Recent examples | 59,821 NOCK (nonce 461), 69,792 NOCK, 12,819 NOCK (nonce 460) — ~$100–700 each |

**Reading:** the mint history is a **many-small-deposits migration** to 181+ distinct recipients over 8 months,
not a single large mint to one sink. The nonce is strictly monotonic through 462. This is consistent with a
genuinely operating bridge and is the empirical bound on how the 5 keys + off-chain machine have behaved.

> **Note on the sum gap.** Pagination captured 447 of ~462 deposits (≈1.243 B), vs. totalSupply ≈1.315 B — a
> ~72 M gap consistent with the ~15 un-paged events (a single deposit reaches 52 M). The gap is a data-fetch
> artifact, **not** evidence of a mint outside `submitDeposit`: the premine/alternate-path question is settled
> exactly and independently by the event-count proof in §1, which does not depend on summing every deposit.
> (Burns can only *reduce* supply below the mint sum, so `Σmint ≥ totalSupply`; the observed `Σsample < supply`
> is purely the missing 15 events.)

## 3. Reserve integrity (value side)
The pool's real `balanceOf(USDC)` and `balanceOf(NOCK)` equal its `getReserves()` **exactly** at snapshot — no
donated/ skimmable imbalance. USDC reserve ≈ **315.6k** is the realizable value an unlimited mint would extract.
