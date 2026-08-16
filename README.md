# Nock Bridge Token — Audit Source Map (Base)

Defensive-security audit package for the **Nock** cross-chain bridge token on **Base (chainid 8453)**.
This repository contains the full source of the target **and of every contract its security depends on**,
in both directions of the trust graph, plus live on-chain state, empirical simulation of what an
unprivileged caller can reach, integrity checks against canonical upstreams, and a prominent list of
what remains genuinely unresolved (→ [`UNRESOLVED.md`](UNRESOLVED.md)).

> **Scope note.** This package *maps* the attack surface; it does **not** judge exploitability. Its job is
> to guarantee that when the audit opens it, nothing bearing on Nock's security is unread, unrecovered, or
> unnamed.

- **Target:** `Nock` (NOCK) — `0x9b5e262cf9bb04869ab40b19af91d2dc85761722`
- **Decimals:** 16 (Nockchain "nicks" alignment) · **totalSupply:** ~1.315 B NOCK
- **Confirmed liquidity / value-at-risk:** ~**$316k USDC** in the Aerodrome vAMM‑USDC/NOCK pool `0x85f1aa3a…`
- **Snapshot block:** see [`data/live_state.json`](data/live_state.json) (Base block ~50,030,000+, resolved live)

---

## TL;DR — the security model in three sentences

1. **NOCK is a faucet controlled by 5 keys, 3-of-5.** The only way NOCK is ever minted is
   `MessageInbox.submitDeposit(...)`, which mints an arbitrary amount to an arbitrary recipient on **3 valid
   signatures from a fixed set of 5 bridge-node addresses**. Those 5 keys are plain EOAs (hot wallets).
2. **The same 5 keys, 3-of-5, are also the admin.** Nock's owner and the inbox's owner are **one Gnosis Safe
   (v1.4.1, 3-of-5) whose owners are the exact same 5 addresses as the bridge nodes.** That Safe can rewrite
   the mint logic (upgrade the UUPS inbox), swap bridge signers, or repoint Nock at a new inbox. There is **no
   separation** between the operator role and the admin role, and **no timelock**.
3. **The value is the pool's USDC.** An unlimited mint converts to real money by swapping NOCK→USDC in the
   Aerodrome pool, which currently holds ~**315k USDC**. Everything downstream/upstream that could enable that
   is in this repo as readable source; the parts that have **no bytecode to read** — the 5 signer keys and the
   off-chain Nockchain→Base bridge that decides what they sign — are named and evidenced in
   [`UNRESOLVED.md`](UNRESOLVED.md) and [`docs/06_offchain_components.md`](docs/06_offchain_components.md).

Every contract in the graph is **verified source** (no decompilation was required); the OpenZeppelin baseline
is **byte-identical to canonical npm v5.5.0** (see [`docs/08_integrity_checks.md`](docs/08_integrity_checks.md)),
so a diff-based review is **not** blind.

---

## The trust graph

```
                          ┌───────────────────────────────────────────────┐
                          │  OWNER SAFE  (Gnosis Safe v1.4.1, 3-of-5)      │
                          │  0xdc37…4288                                   │
                          │  owners = the 5 bridge-node EOAs (see below)   │
                          └───────────────┬───────────────┬───────────────┘
             owns (can updateInbox)       │               │  owns (onlyOwner):
             ┌────────────────────────────┘               │  upgradeTo / updateBridgeNode /
             │                                             │  setWithdrawalsEnabled
             ▼                                             ▼
   ┌───────────────────────┐  mint (onlyInbox)   ┌────────────────────────────────────────┐
   │  TARGET: Nock (NOCK)  │◄────────────────────│  MessageInbox  (UUPS proxy → impl)      │
   │  0x9b5e…1722          │                     │  proxy 0x2033…8021 → impl 0xcf69…be99   │
   │  ERC20, 16 dp         │  notifyBurn ───────►│  submitDeposit(): 3-of-5 signed → mint  │
   └───────────┬───────────┘                     └───────────────────┬────────────────────┘
               │ token1 in pool                                      │ verifies signatures from
               ▼                                                     ▼
   ┌───────────────────────────────────────┐          ┌──────────────────────────────────────┐
   │  Aerodrome vAMM-USDC/NOCK pool         │          │  bridgeNodes[5]  (3-of-5 mint quorum) │
   │  0x85f1aa3a…  (EIP-1167 clone of       │          │  0x091f… 0xcade… 0x79a2… 0xddde…     │
   │  canonical Aerodrome Pool 0xa4e4…d6d7) │          │  0xf044…  — ALL EOAs (hot keys)       │
   │  holds ~315k USDC  ◄── value-at-risk   │          │  == the Safe's 5 owners (SAME keys)  │
   └───────────┬───────────────────────────┘          └──────────────────────────────────────┘
               │ token0                                        ▲
               ▼                                               │ decides what to sign (OFF-CHAIN)
   ┌───────────────────────┐                       ┌───────────────────────────────────────────┐
   │  USDC (canonical      │                       │  Nockchain-side bridge / Hoon state machine │
   │  Circle FiatToken)    │                       │  — no bytecode, see UNRESOLVED.md           │
   └───────────────────────┘                       └───────────────────────────────────────────┘

  LP ownership of the pool (who can pull the 315k liquidity — value owners, not token authorities):
    49.6%  V2Locker instance 0x876B…2E48  (lock EXPIRED 2026-06-22; owner 0xb51a…f294 can withdraw)
    28.9%  EIP-7702 smart-account EOA 0x078C…d4c9
    16.3%  EOA 0xdeb9…41a2   ·   rest dust
```

**Direction 1 — what the target leans on (downstream):** Nock → `inbox` (MessageInbox proxy → impl) → the 5
bridge-node signer keys → back-reference to Nock. Nock also lives as `token1` in the Aerodrome pool, whose
`token0` is canonical USDC. All resolved; graph stops growing here.

**Direction 2 — what holds power over the target (upstream):** the **Owner Safe** (mint-logic upgrade, signer
replacement, inbox repointing) and, one layer down, the **3-of-5 bridge nodes** (direct minting). The Safe's
owners **are** the bridge nodes, so both branches collapse to the **same 5 keys**.

---

## Repository layout

| Path | What it is | Address | Verified |
|------|-----------|---------|:--------:|
| [`src/1-target/nock/`](src/1-target/nock) | **Nock** target token (ERC20 + Ownable) | `0x9b5e…1722` | ✅ source |
| [`src/2-mint-authority/message-inbox-impl/`](src/2-mint-authority/message-inbox-impl) | **MessageInbox** implementation — the mint logic | `0xcf69…be99` | ✅ source |
| [`src/2-mint-authority/inbox-proxy-erc1967/`](src/2-mint-authority/inbox-proxy-erc1967) | ERC1967 UUPS proxy shell (the live `inbox`) | `0x2033…8021` | ✅ source |
| [`src/3-admin-owner/owner-safe-proxy/`](src/3-admin-owner/owner-safe-proxy) | Owner **SafeProxy** (owns Nock + inbox) | `0xdc37…4288` | ✅ source |
| [`src/3-admin-owner/safe-l2-singleton/`](src/3-admin-owner/safe-l2-singleton) | Safe **v1.4.1 SafeL2** singleton | `0x29fc…c762` | ✅ canonical |
| [`src/3-admin-owner/safe-fallback-handler/`](src/3-admin-owner/safe-fallback-handler) | CompatibilityFallbackHandler | `0xfd07…ec99` | ✅ canonical |
| [`src/4-value-path/aerodrome-pool-impl/`](src/4-value-path/aerodrome-pool-impl) | Aerodrome **Pool** impl (clone target) | `0xa4e4…d6d7` | ✅ canonical |
| [`src/4-value-path/aerodrome-pool-factory/`](src/4-value-path/aerodrome-pool-factory) | Aerodrome **PoolFactory** | `0x420d…40da` | ✅ canonical |
| [`src/4-value-path/usdc-proxy/`](src/4-value-path/usdc-proxy) + [`usdc-impl/`](src/4-value-path/usdc-impl) | Canonical Circle **USDC** (proxy + FiatTokenV2_2) | `0x8335…2913` | ✅ canonical |
| [`src/4-value-path/v2-locker/`](src/4-value-path/v2-locker) | **V2Locker** holding 49.6% of pool LP | `0x11bc…e60d` | ✅ source |

> The Aerodrome pool `0x85f1aa3a…` itself is a 45-byte EIP-1167 minimal-proxy **clone**; its runtime logic is
> the `aerodrome-pool-impl` above, which is byte-for-byte `factory.implementation()` (verified live). See
> [`docs/08_integrity_checks.md`](docs/08_integrity_checks.md).

### Documentation

| Doc | Contents |
|-----|----------|
| [`docs/01_trust_graph.md`](docs/01_trust_graph.md) | Full both-directions trust graph, every edge, why each address is reached |
| [`docs/02_live_state.md`](docs/02_live_state.md) | Human-readable live-state snapshot |
| [`docs/03_authorities.md`](docs/03_authorities.md) | Who holds every privileged power **right now**, and the exact function that grants it |
| [`docs/04_mint_path_analysis.md`](docs/04_mint_path_analysis.md) | `submitDeposit` guard-by-guard analysis (replay, nonce, signature scheme) |
| [`docs/05_simulation_results.md`](docs/05_simulation_results.md) | Empirical eth_call probes from an unprivileged EOA — what reverts vs. reaches |
| [`docs/06_offchain_components.md`](docs/06_offchain_components.md) | Off-chain trust: the 5 signer keys + the Nockchain→Base bridge, with on-chain evidence |
| [`docs/07_deposit_history_evidence.md`](docs/07_deposit_history_evidence.md) | No-premine proof, upgrade history, deposit-amount distribution |
| [`docs/08_integrity_checks.md`](docs/08_integrity_checks.md) | OZ byte-diff vs npm v5.5.0, Safe/pool/USDC canonical verification |
| [`docs/09_exploit_review.md`](docs/09_exploit_review.md) | **Exploitation audit** — properties, adversarial review of every bespoke path, killed candidates |
| [`docs/10_entrypoint_coverage.md`](docs/10_entrypoint_coverage.md) | **Complete entry-point enumeration** — every external/public function, its guard, one-line reason not exploitable |
| [`UNRESOLVED.md`](UNRESOLVED.md) | **Everything that could not be followed on-chain** — read this |

### Data & tools

- [`data/live_state.json`](data/live_state.json) — machine-readable snapshot (authorities, reserves, history facts)
- [`data/source_manifest.json`](data/source_manifest.json) — address → path map for every package
- [`data/simulation_results.txt`](data/simulation_results.txt) — raw simulation output
- [`tools/`](tools) — the exact scripts used (RPC helper, simulators, evidence/history scanners) for reproducibility

---

## What is resolved vs. what is not

**Resolved (in this repo as readable code + live state + evidence):** the target, the mint logic, the proxy
shell, the admin Safe and its configuration, the value pool and its real reserves, the LP owners, the USDC leg,
the historical mint/upgrade record. Every on-chain hop was followed until the graph stopped growing.

**Not resolvable on-chain (named + evidenced in [`UNRESOLVED.md`](UNRESOLVED.md)):** the 5 bridge-node **private
keys** and the **off-chain Nockchain→Base bridge** (the "Hoon state machine" the code comments name) that
decides which deposits the 5 keys sign. These have no bytecode and no address to simulate; they are the real
root of trust, and their behavior is bounded here only by the historical deposit record.
