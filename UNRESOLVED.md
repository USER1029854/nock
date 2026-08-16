# UNRESOLVED — what could not be followed on-chain

Everything with on-chain bytecode in Nock's trust graph was resolved to **verified source** and its live state
read (see [`README.md`](README.md) and [`docs/`](docs)). What remains below has **no bytecode to read and no
address to simulate** — it is the genuine root of trust. Each item states *what decision it controls*, *what
goes wrong if it is wrong or compromised*, and *the on-chain evidence that bounds its behavior*.

Read this list as the frontier of the audit: the on-chain contracts are only as trustworthy as these.

---

## 1. The 5 bridge-node signing keys — **the actual mint authority** 🔴 CRITICAL

| | |
|---|---|
| **Addresses** | `0x091f5a663dba081547d60bf0aa50d0a56f1e0964`, `0xcadeeee25c168b8cf054f290f97dbf568a853f64`, `0x79a2740620d989d51e08f0de494f520e95e5b9cb`, `0xddde747a20b17ea13f4c4eeb77615b1f18ca0b3b`, `0xf0441e68e994c20c998e54a23f0d40b76185be76` |
| **On-chain form** | Plain **EOAs** (hot wallets). No bytecode. |
| **What they control** | `MessageInbox.submitDeposit()` mints **any amount to any recipient** on **3 valid signatures** from this set. These same 5 addresses are **also** the 3-of-5 owners of the Owner Safe, so they *additionally* control upgrades, signer replacement, and inbox repointing. |
| **What goes wrong if compromised** | **3 of these 5 private keys = unlimited NOCK mint** → swap to drain the ~315k USDC pool (and any future liquidity). No on-chain circuit-breaker caps per-deposit or total mint. Key custody is entirely off-chain and unknowable from the chain. |
| **Evidence bounding behavior** | All 5 are live EOAs with real activity (49–145 txs each, small ETH balances — operational hot wallets, not cold storage). They have authorized **462 deposits** (`lastDepositNonce`) of **modest, plausible amounts** (recent: 12k–70k NOCK; historical max single deposit ≈ **52.3 M NOCK**). No anomalous single mint of the whole supply. See [`docs/07_deposit_history_evidence.md`](docs/07_deposit_history_evidence.md). |
| **Open question for the audit** | Where do these 5 keys live, how are they generated/stored, and is there any m-of-n custody or HSM behind them? Are any two co-located (correlated compromise)? On-chain cannot answer. |

---

## 2. The off-chain Nockchain→Base bridge ("Hoon state machine") — **decides what gets signed** 🔴 CRITICAL

| | |
|---|---|
| **On-chain form** | None. Named explicitly in `MessageInbox` code comments: *"The off-chain Hoon state machine tracks deposits but cannot prevent replay because it is not the final arbiter of token minting — this contract is."* |
| **What it controls** | The correspondence between a **real Nockchain deposit/lock** and a **Base mint instruction**. It computes the `txId / nameFirst / nameLast / amount / blockHeight / asOf` tuple the 5 nodes sign. The Base contract verifies **signatures**, not **truthfulness** — it never checks that a Nockchain deposit actually happened. |
| **What goes wrong if wrong/compromised** | If this component credits a deposit that did not occur (bug, or operator compromise), the 5 nodes sign it and the inbox mints **unbacked** NOCK. This is the classic bridge failure mode: the on-chain token can be flawless and still be inflated because the thing that decides *what is true* lives off-chain. |
| **Evidence bounding behavior** | The `DepositProcessed` event log is the only on-chain window: **462** processed deposits, strictly-monotonic nonce, **181 distinct recipients**, amounts consistent with a real migration (`decimals=16` "nicks" precision). No evidence in the record of mints to a single attacker-like sink. But the record only shows what *was* signed, not whether each had genuine Nockchain backing — that is unverifiable from Base. |
| **Open question for the audit** | What proves a Nockchain deposit to the off-chain machine (a light client? a trusted indexer of Nockchain?)? Is the `asOf` causality hash checked against anything, or is it advisory? Who runs this machine and can it be made to emit a false deposit tuple? |

---

## 3. Nockchain-side withdrawal settlement — **honors burns** 🟠

| | |
|---|---|
| **On-chain form** | None (the Nockchain side). On Base, `Nock.burn(amount, lockRoot)` burns tokens, emits `BurnForWithdrawal`, and calls `MessageInbox.notifyBurn()` (which only reverts if `withdrawalsEnabled==false`). |
| **What it controls** | Whether a Base-side burn actually releases the corresponding Nockchain assets to the user's `lockRoot`. Entirely off-chain. |
| **What goes wrong if wrong/compromised** | Burns could be un-honored (user loses NOCK, gets nothing on Nockchain) or double-honored. This does not drain the Base USDC pool, but it is part of the bridge's trust path and a user-fund risk. |
| **Evidence bounding behavior** | `withdrawalsEnabled == true` right now; the toggle is owner-only (the Safe). `notifyBurn` correctly gates on `msg.sender == nock`. The Base side of the burn is sound; the settlement is not observable from Base. |

---

## 4. Off-chain identity & custody behind the privileged addresses 🟠

- **Owner Safe key custody** — the Safe (`0xdc37…4288`) is a canonical, correctly-configured 3-of-5 Safe with **no modules and no guard** (verified), but its security reduces entirely to the same 5 EOA keys in item 1. No timelock sits between a 3-of-5 signature and a mint-logic upgrade.
- **V2Locker owner** `0xb51ae43a65bb89c441c6ec51a3e9f0a164fff294` — controls the withdrawal of **49.6% of the pool LP**. The lock **already expired (2026-06-22)**, so this key can pull that liquidity now. On-chain identity unknown (EOA). LP withdrawal returns the LP's own pro-rata USDC+NOCK; it collapses the market but does not steal others' funds.
- **Deployer** `0x4356D2C1B6f7238dcEE0a6E90c9B5B1717648555` (EOA) — bootstrapped the system; holds no current on-chain role (ownership is the Safe). Real-world identity unknown.
- **Locker factory** `0x067b028c66f61466f66864cc01f92afc7d99e530` — third-party locker service that deployed the V2Locker instance; its own admin powers over locker instances were not fully enumerated (peripheral to token mint-security; the LP it guards is value-owner funds, not token authority).

---

## 5. Second trading venue (named, not fully mapped) 🟡

A holder tagged **Uniswap V4 `PoolManager`** (`0x498581fF718922c3f8e6A244956aF099B2652b2b`) holds ~15.6 M NOCK,
indicating a **second NOCK pool exists on Uniswap V4** beyond the confirmed Aerodrome pool. The V4 PoolManager
is canonical Uniswap infrastructure (singleton, verified). This is an **additional value venue** an unlimited
mint could also drain; its paired asset and depth were not enumerated here because the confirmed liquidity in
scope is the Aerodrome pool. **Flagged for the audit** if total drainable value matters.

---

## Minor / transparency notes (not trust holes)

- **Deposit-sum cross-check gap.** Summing `DepositProcessed.amount` over Blockscout pagination captured **447 of
  ~462** events (≈1.243 B NOCK) vs. live totalSupply ≈1.315 B; the ~72 M gap is consistent with the ~15 un-paged
  events (max single deposit alone is 52 M). The **premine question is closed independently and exactly** by the
  event-count proof in [`docs/07`](docs/07_deposit_history_evidence.md) (`InboxUpdated`=1, `Upgraded`=1), which
  does not depend on summing every deposit.
- No contract in the graph required decompilation — all are verified source — so there is **no "opaque blob"**
  in the on-chain value path. The unresolved frontier is entirely **off-chain** (items 1–3).
