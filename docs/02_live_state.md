# 02 · Live-state snapshot

Read from Base mainnet at **block ≈ 50,030,989**. Machine-readable copy: [`../data/live_state.json`](../data/live_state.json).
Source constants (e.g. the constructor `inbox` argument) are **not** trusted — every value below is read from
current chain storage. (The Nock constructor set `inbox = address(0)`; the real inbox was wired later — so live
reads are mandatory, not source reads.)

## Target — Nock `0x9b5e262cf9bb04869ab40b19af91d2dc85761722`
| Field | Live value |
|---|---|
| name / symbol | `Nock` / `NOCK` |
| decimals | **16** |
| totalSupply | 13,151,530,078,255,920,410,156,250 nicks = **~1,315,153,008 NOCK** |
| `inbox()` | **`0x2033e72869c729b5a10f9c0a9d087c8297518021`** (MessageInbox proxy) |
| `owner()` | **`0xdc373766c03c645f04695224527ba7ef61fd4288`** (Owner Safe) |

## MessageInbox — proxy `0x2033…8021` → impl `0xcf69…be99`
| Field | Live value |
|---|---|
| proxy type | ERC1967 **UUPS** (admin slot = `0x0`) |
| implementation (eip1967 slot, live) | **`0xcf6900c9fef4b3723856703e90a61d63a28dbe99`** |
| `owner()` | `0xdc37…4288` (**same Safe** as Nock owner) |
| `nock()` | `0x9b5e…1722` (back-ref to target) |
| `withdrawalsEnabled()` | **true** |
| `lastDepositNonce()` | **462** |
| `THRESHOLD()` | **3** (of 5) |
| `VERSION()` | `1.0.0` |
| `bridgeNodes[0..4]` | `0x091f5a66…0964`, `0xcadeeee2…3f64`, `0x79a27406…b9cb`, `0xddde747a…0b3b`, `0xf0441e68…be76` |

## Owner Safe — `0xdc37…4288`
| Field | Live value |
|---|---|
| type | Gnosis **Safe v1.4.1** (`VERSION()` = 1.4.1) |
| singleton (slot 0) | `0x29fcb43b46531bca003ddc8fcb67ffe91900c762` (canonical SafeL2 v1.4.1) |
| `getThreshold()` | **3** |
| `getOwners()` | the **same 5 addresses** as `bridgeNodes` above |
| `nonce()` | **1** (only one Safe tx ever executed) |
| modules | **none** (`getModulesPaginated` → empty) |
| guard | **none** (`0x0`) |
| fallback handler | `0xfd0732dc9e303f09fcef3a7388ad10a83459ec99` (canonical CompatibilityFallbackHandler) |

## Aerodrome pool — `0x85f1aa3a…` (vAMM-USDC/NOCK)
| Field | Live value |
|---|---|
| type | volatile (stable = false), 45-byte EIP-1167 clone |
| clone implementation | `0xa4e46b4f701c62e14df11b48dce76a7d793cd6d7` (= `factory.implementation()`) |
| factory | `0x420dd381b31aef6683db6b902084cb0ffece40da` (Aerodrome PoolFactory) |
| token0 / token1 | USDC `0x8335…2913` / NOCK `0x9b5e…1722` |
| reserve0 (USDC) | **315,623.86 USDC** — real `balanceOf` == `getReserves`, no skim skew |
| reserve1 (NOCK) | 31,742,168.6 NOCK |
| LP totalSupply | 0.31634 (18-dp) |
| swap fee | 0.30% (`factory.getFee`) · pool **not paused** |
| gauge | `0x4cbb6188…c3db` — **killed** (`isAlive=false`, ~0 LP staked) |

## LP ownership of the pool (value owners)
| Holder | Type | Share | Note |
|---|---|---|---|
| `0x876B24D1…2E48` | **V2Locker** instance | **49.6%** | lock `lockedUntil` = 2026-06-22 → **EXPIRED**; owner `0xb51a…f294` can withdraw |
| `0x078C1D2b…d4c9` | EIP-7702 smart EOA | 28.9% | MetaMask DeleGator delegation |
| `0xdeb95D65…41a2` | EOA | 16.3% | |
| others | — | ~5% | dust |

## History facts (see [`07_deposit_history_evidence.md`](07_deposit_history_evidence.md))
| Field | Value |
|---|---|
| `InboxUpdated` events, all time | **1** (block 39,685,415: `0x0` → MessageInbox proxy) |
| `Upgraded` events, all time | **1** (block 39,685,413: impl → current `0xcf69`; **never upgraded since**) |
| Deposits processed (nonce) | 462, across ~8 months |
| Premine | **none** |
