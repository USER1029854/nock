# 08 · Integrity checks — are the shared building blocks genuine?

A diff-based review is blind if the "known-good" baseline was itself doctored. Every shared/upstream building
block in the graph is therefore checked against **real upstream** (npm / canonical deployments), not against a
copy shipped with the project.

## 1. OpenZeppelin — byte-identical to canonical npm v5.5.0 ✅

The bundled OZ files (as verified on Etherscan) were diffed **byte-for-byte** against the pristine
`@openzeppelin/contracts@5.5.0` and `@openzeppelin/contracts-upgradeable@5.5.0` packages fetched fresh from the
npm registry. Method: [`tools`](../tools) + `diff`.

| Package | OZ files compared | Result |
|---|---|---|
| Nock (`src/1-target/nock`) | ERC20, IERC20, IERC20Metadata, Ownable, Context, draft-IERC6093 | **6 / 6 identical** |
| MessageInbox (`src/2-mint-authority/message-inbox-impl`) — OZ contracts | ERC20, proxy/ERC1967Utils, UUPSUpgradeable, StorageSlot, Address, LowLevelCall, … | **16 / 16 identical** |
| MessageInbox — OZ **upgradeable** | Initializable, UUPSUpgradeable, OwnableUpgradeable, ContextUpgradeable | **4 / 4 identical** |

**Zero** modifications. In particular, ERC20 `_update` / `_mint` / `_transfer`, `Ownable`, and the UUPS/
Initializable machinery are stock. **No hidden backdoor in the "library" layer.** The only bespoke Solidity in
the mint/admin path is `Nock.sol` and `MessageInbox.sol` — both small, both fully read (docs [01](01_trust_graph.md),
[04](04_mint_path_analysis.md)).

## 2. Proxies resolved to real implementations ✅

| Proxy | Method | Live implementation | Verified |
|---|---|---|---|
| Inbox `0x2033…8021` (ERC1967 UUPS) | read `eip1967.implementation` storage slot | `0xcf69…be99` = `MessageInbox` | ✅ + upgrade history = 1 (never changed) |
| Aerodrome pool `0x85f1aa3a…` (EIP-1167 clone) | parsed 45-byte clone bytecode **and** compared to `factory.implementation()` | `0xa4e46b4f…d6d7` = `Pool` | ✅ clone target **==** factory blessed impl |
| USDC `0x8335…2913` (FiatTokenProxy) | read impl | `0x2ce6311d…fd779` = `FiatTokenV2_2` | ✅ canonical Circle |

The pool clone check is the important one: the 45-byte minimal proxy points at exactly the address
`factory.implementation()` returns, so the pool runs Aerodrome's blessed `Pool` logic — it was **not** re-pointed
at a doctored implementation.

## 3. Gnosis Safe — canonical v1.4.1 ✅

| Component | Address | Check |
|---|---|---|
| Owner Safe singleton (slot 0) | `0x29fcb43b46531bca003ddc8fcb67ffe91900c762` | Canonical **SafeL2 v1.4.1** deterministic-deploy address; verified source `SafeL2`; `VERSION()` returns `1.4.1`. |
| Fallback handler | `0xfd0732dc9e303f09fcef3a7388ad10a83459ec99` | Canonical **CompatibilityFallbackHandler** v1.4.1. |
| Modules / guard | — | **none** / **none** — no extension code can move Safe funds or bypass the 3-of-5. |

The Safe uses the standard singleton at its canonical cross-chain address with no custom module or guard, so its
behavior is the audited Safe behavior; the only trust reduction is to its 5 owner keys.

## 4. Canonical external venue/asset ✅
- **USDC** `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913` — the canonical Circle USDC on Base (FiatTokenProxy →
  FiatTokenV2_2). Standard, verified; source included in [`../src/4-value-path/`](../src/4-value-path) for
  completeness as the drained asset.
- **Aerodrome PoolFactory** `0x420dd381b31aef6683db6b902084cb0ffece40da` — canonical; `getFee`=0.30%, pool not
  paused; `pauser`/`feeManager` = Aerodrome governance Safe `0xe6a4…2075` (can pause/adjust-fee the pool, no
  power over NOCK mint).

## 5. Bespoke code inventory (what actually needs human eyes)
| File | Address | Size | In value path? |
|---|---|---|:--:|
| `Nock.sol` | `0x9b5e…1722` | ~2.8 KB | **yes** (the token) |
| `MessageInbox.sol` | `0xcf69…be99` | ~11 KB | **yes** (the mint authority) |
| `V2Locker` (+ Locker base) | `0x11bc…e60d` | ~medium | LP custody only (not mint/authority) |

Everything else in the repo is canonical/library code confirmed genuine above. **The diff-based review is not
blind:** the surface that needs judgment is these three, and all three are present as verified source.
