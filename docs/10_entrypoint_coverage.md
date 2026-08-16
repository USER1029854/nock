# 10 · Entry-point coverage (complete enumeration)

Every externally-reachable entry point across the in-scope contracts, built mechanically from the source
(`grep` of every `public`/`external` function, inherited functions included, plus auto-generated public-getter
and `fallback`/`receive` surface), each with its guard and a one-line reason it is not exploitable by a hostile
**unprivileged** caller — or a note that it is. This is the checkable basis for the verdict in
[`09_exploit_review.md`](09_exploit_review.md).

## Scope decision (stated so it's checkable)
- **Exhaustively enumerated (bespoke / project code):** `Nock`, `MessageInbox` (+ its ERC1967 proxy shell),
  and the velodrome `V2Locker` / `Locker` / `V2LockerFactory` that hold project LP. Inherited OZ functions that
  are **live on these deployed contracts** (ERC20, Ownable/Upgradeable, UUPS) are enumerated as real entry
  points.
- **Boundary-accounted (canonical, byte-verified — [`08`](08_integrity_checks.md)):** Gnosis Safe v1.4.1,
  Aerodrome Pool/PoolFactory, Circle USDC. Their full internal function surface is the audited upstream surface
  and is **not** re-enumerated line-by-line; instead every point where the bespoke system calls into or is
  called by them is accounted for below under "Canonical boundaries." **Assumption:** these equal their audited
  upstream (verified byte-identical for OZ; via singleton/clone/proxy identity for Safe/Aerodrome/USDC). If one
  were secretly modified, that conclusion changes — but the on-chain identity checks in doc 08 make that
  observable.

Legend: 🟢 not exploitable · 🟡 out-of-scope class (noted) · 🔴 finding. "unpriv." = arbitrary unprivileged caller.

---

## A. Nock — `0x9b5e…1722` (non-upgradeable; ERC20 + Ownable)

| # | Entry point | Guard | Reason not exploitable |
|---|---|---|---|
| A1 | `mint(address,uint256)` | `msg.sender == inbox` | 🟢 Only the MessageInbox proxy passes; unpriv. → revert "Only inbox can mint" (simulation-confirmed). Sole supply-creation path. |
| A2 | `burn(uint256,bytes32)` | `balanceOf(msg.sender) ≥ amount` | 🟢 Destroys the caller's **own** tokens; releases nothing on-chain (`notifyBurn` is `view`). Can't burn another's balance. |
| A3 | `updateInbox(address)` | `onlyOwner` | 🟢 Owner = Safe; unpriv. → `OwnableUnauthorizedAccount`. |
| A4 | `decimals()` | none (pure) | 🟢 Returns constant 16. No state. |
| A5 | `cap()` | none (pure) | 🟢 Returns 0 and is **read nowhere** — dead/informational; enforces nothing, so its value is irrelevant. |
| A6 | `inbox()` getter | none (view) | 🟢 Read-only. |
| A7 | `transfer(address,uint256)` | balance | 🟢 Standard OZ v5.5.0; moves caller's own tokens. |
| A8 | `approve(address,uint256)` | none | 🟢 Sets caller's own allowance only. |
| A9 | `transferFrom(address,address,uint256)` | allowance | 🟢 Standard OZ checked allowance; needs a grant from `from`. No contract here holds an exploitable standing allowance. |
| A10 | `allowance/balanceOf/name/symbol/totalSupply` | none (view) | 🟢 Read-only. |
| A11 | `owner()` | none (view) | 🟢 Read-only. |
| A12 | `renounceOwnership()` | `onlyOwner` | 🟢 Unpriv. → revert. (Owner-only.) |
| A13 | `transferOwnership(address)` | `onlyOwner` | 🟢 Unpriv. → revert. |
| A14 | (no `receive`/`fallback`) | — | 🟢 Plain ETH send reverts; contract holds no ETH and has no sweep, so nothing to extract. |

## B. MessageInbox — proxy `0x2033…8021` → impl `0xcf69…be99` (UUPS; Ownable/Initializable)

| # | Entry point | Guard | Reason not exploitable |
|---|---|---|---|
| B1 | `submitDeposit(Tip5,Tip5,Tip5,address,uint256,uint256,Tip5,uint256,bytes[])` | 3-of-5 node ECDSA sigs; `processedDeposits[txId]`; `depositNonce > lastDepositNonce`; Tip5 range checks | 🟢 The only mint trigger. Robust recovery (len 65, `0<s≤N/2`, `v∈{27,28}`, signer≠0), per-node dedup, replay + monotonic-nonce guards, all fields fixed-size (no `encodePacked` ambiguity). Forgery = ECDSA break; valid non-node sigs rejected (simulation-confirmed). See [`04`](04_mint_path_analysis.md). |
| B2 | `initialize(address[5],address)` | `initializer` | 🟢 Already consumed at deploy (owner = Safe); re-call → `InvalidInitialization`. |
| B3 | `updateBridgeNode(uint256,address)` | `onlyOwner` | 🟢 Unpriv. → revert. |
| B4 | `setWithdrawalsEnabled(bool)` | `onlyOwner` | 🟢 Unpriv. → revert. |
| B5 | `notifyBurn()` | `view` + `msg.sender == nock` | 🟢 Only Nock; performs no state change/value move (revert-check only). |
| B6 | `upgradeTo(address)` | `onlyOwner` | 🟢 Unpriv. → revert. |
| B7 | `upgradeToAndCall(address,bytes) payable` | `onlyProxy` + `_authorizeUpgrade` `onlyOwner` | 🟢 Unpriv. → revert (owner). `payable`, but reverts before consuming value. |
| B8 | `proxiableUUID()` | `notDelegated` (view) | 🟢 Via the proxy it reverts by design; read-only otherwise. |
| B9 | `owner()` / `renounceOwnership()` / `transferOwnership(address)` | view / `onlyOwner` | 🟢 Read-only or owner-only. |
| B10 | getters: `VERSION, bridgeNodes(uint256), THRESHOLD, processedDeposits(bytes32), lastDepositNonce, withdrawalsEnabled, nock` | none (view) | 🟢 Read-only. |
| B11 | proxy `fallback() payable` (ERC1967Proxy) | delegatecall to impl | 🟢 Exposes exactly B1–B10. No Transparent-proxy admin function exists (UUPS); ETH with empty/unknown calldata → impl has no `receive` → reverts. |

## C. V2Locker instance — `0x876B…2E48` (velodrome; holds ~49.6% pool LP)

| # | Entry point | Guard | Reason not exploitable |
|---|---|---|---|
| C1 | `initialize(address,address,uint256,uint32,address,uint16,uint16)` | `initializer` | 🟢 Consumed; re-call reverts. |
| C2 | `unlock(address,address)` | `msg.sender == factory` (+ `onlyLocked`) | 🟢 The only path that moves principal LP; unpriv. → revert "NotFactory". Factory re-gates on owner+expiry (D2). |
| C3 | `stake()` | `onlyOwner` (+`onlyLocked`,`ensureGauge`) | 🟢 Unpriv. → revert; only deposits locker's own LP into the gauge. |
| C4 | `unstake()` | `onlyOwner` (+`onlyLocked`) | 🟢 Unpriv. → revert; LP returns to the locker, not to caller. |
| C5 | `claimFees(address)` | `onlyOwner` (+`onlyLocked`) | 🟢 Unpriv. → revert; pays fees to owner-chosen recipient. |
| C6 | `claimRewards(address)` | `onlyOwner` (+`onlyLocked`) | 🟢 Unpriv. → revert. |
| C7 | `bribe(uint16)` | `onlyOwner` (+`onlyLocked`,`ensureGauge`) | 🟢 Unpriv. → revert; `_percentage ≤ bribeableShare`; remainder to owner. |
| C8 | `increaseDuration(uint32)` | `onlyOwner` | 🟢 Unpriv. → revert; can only extend the lock. |
| C9 | `increaseLiquidity(uint256,uint256,uint256,uint256)` | `onlyOwner` (+`onlyLocked`) | 🟢 Unpriv. → revert; pulls funds from caller (owner), refunds leftovers to owner; router approval reset to 0 after. |
| C10 | `setBribeableShare(uint16)` | `onlyOwner` | 🟢 Unpriv. → revert; `≤ MAX_BPS`. |
| C11 | `owner()`/`renounceOwnership()`/`transferOwnership(address)` | view / `onlyOwner` | 🟢 Owner-only; `_transferOwnership` also updates factory bookkeeping (D4). |
| C12 | getters: `factory,rewardToken,root,voter,pool,token0,token1,gauge,lp,beneficiary,beneficiaryShare,bribeableShare,lockedUntil,staked,router` | none (view) | 🟢 Read-only. |
| C13 | (no `receive`/`fallback`) | — | 🟢 ETH send reverts; no ETH held. |

## D. V2LockerFactory — `0x067b…e530` (velodrome; the locker's gate)

| # | Entry point | Guard | Reason not exploitable |
|---|---|---|---|
| D1 | `lock(address,uint256,uint32,address,uint16,uint16,address)` | permissionless; pulls `_lp` via `transferFrom(msg.sender,…)` | 🟢 Creates a locker from the **caller's own** LP (must own+approve). Cannot touch anyone else's locker/LP. |
| D2 | `unlock(address,address)` | `msg.sender == locker.owner()` **and** `block.timestamp ≥ lockedUntil` **and** `!staked` | 🟢 Unpriv. → `NotLockerOwner`/`Locked`. Owner-only, post-expiry. |
| D3 | `migrate(address,uint256,uint256,uint256,uint256)` | `msg.sender == locker.owner()` (or `poolLauncher`) + still-locked + `newLockerFactory != 0` | 🟢 Unpriv. → `NotLockerOwner`. Owner-only; moves LP only into a factory-blessed new locker. |
| D4 | `transferLockerOwnership(address,address,address)` | `instances[msg.sender]` (caller must be a locker) | 🟢 Unpriv. → `NotLocker`. Updates enumeration bookkeeping only; moves no value, changes no real `Ownable.owner`. |
| D5 | `setNewLockerFactory(address)` | `onlyOwner` (factory admin) | 🟢 Unpriv. → revert. Factory-admin power; cannot extract a locker's LP. |
| D6 | getters: `lockers,locked,locks,lockersCount,lockersPerUser(…),lockersPerPoolPerUser(…),…` | none (view) | 🟢 Read-only. |

## Canonical boundaries (accounted, not re-enumerated)

| Boundary | Interaction | Why safe for NOCK |
|---|---|---|
| Aerodrome **Pool** `0x85f1aa3a…` | anyone may `swap/mint/burn/skim/sync` | 🟢 Standard audited AMM; trading at market. **No bespoke contract reads its price/reserves**, so there is no price-dependent logic to skew (flash loans included). Realizing a mint-bug via a swap would be in scope, but there is no mint-bug (B1). |
| Aerodrome **PoolFactory** `0x420d…40da` | `getFee`, `pauser`/`feeManager` = Aerodrome gov | 🟡 Can pause/adjust-fee the pool (Aerodrome governance power) — affects trading, not NOCK mint/authority. |
| **USDC** `0x8335…2913` | pool's quote asset; `transfer/transferFrom` | 🟢 Canonical Circle FiatToken; standard, no callback/fee-on-transfer. Its own admin roles are Circle's, outside NOCK's trust. |
| **Safe** `0xdc37…4288` | `execTransaction` etc. | 🟢 Canonical v1.4.1, no modules/guard; every admin action needs 3-of-5. Unpriv. `execTransaction` w/o quorum reverts (simulation-confirmed). |

## Verdict after exhausting the surface
Every entry point above is 🟢 (gated to owner/factory, operates only on the caller's own value, is a pure view,
or is cryptographically gated) or 🟡 (an excluded class, noted). **No 🔴.** The completeness pass specifically
cleared the "unglamorous" functions a value-first triage would skip — `burn`, `cap`, `skim`-adjacent locker
`claimFees`/`bribe`/`unstake`, `transferLockerOwnership`, `setNewLockerFactory`, the inherited ERC20/Ownable
surface, and the proxy fallback — and none is load-bearing in a way an unprivileged caller can abuse. The one
latent, precondition-bound weakness (deposit-signature domain separation) and the off-chain trust root are in
[`09`](09_exploit_review.md) and [`06`](06_offchain_components.md).
