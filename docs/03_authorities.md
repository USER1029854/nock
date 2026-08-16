# 03 · Authorities — who can do what, right now

Every privileged power in the Nock system, the exact function that grants it, the address that currently holds
it, and the on-chain guard that enforces it. All confirmed against live state and by simulation
([`05_simulation_results.md`](05_simulation_results.md)).

## The one fact that dominates everything

> **The 5 bridge-node keys and the 5 Owner-Safe owners are the SAME five addresses, and both use a 3-of-5
> threshold.** So the mint quorum and the admin quorum are one and the same 3-of-5 key set. Nothing in the
> system separates "operate the bridge" from "own the bridge," and there is **no timelock** anywhere.

```
0x091f5a66…0964   0xcadeeee2…3f64   0x79a27406…b9cb   0xddde747a…0b3b   0xf0441e68…be76
        └──────── these 5 EOAs ARE both `bridgeNodes[5]` AND `Safe.getOwners()` ────────┘
   any 3 of 5  ─►  mint arbitrary NOCK (submitDeposit)
   any 3 of 5  ─►  upgrade mint logic / swap signers / repoint inbox / toggle withdrawals (via the Safe)
```

## Power table

| # | Power | Function | Guard (live-verified) | Held by now |
|---|-------|----------|-----------------------|-------------|
| 1 | **Mint arbitrary NOCK** to any recipient | `MessageInbox.submitDeposit()` | 3 valid sigs from `bridgeNodes[5]` + unused nonce + unused txId | **3-of-5 bridge keys** |
| 2 | **Replace the entire mint logic** (UUPS) | `MessageInbox.upgradeTo()` / `upgradeToAndCall()` → `_authorizeUpgrade` | `onlyOwner` | **Owner Safe (3-of-5)** |
| 3 | **Swap any bridge signer** | `MessageInbox.updateBridgeNode(i,newNode)` | `onlyOwner` | **Owner Safe (3-of-5)** |
| 4 | **Repoint Nock at a new inbox** (new mint authority) | `Nock.updateInbox(newInbox)` | `onlyOwner` | **Owner Safe (3-of-5)** |
| 5 | **Disable withdrawals** (brick `burn`) | `MessageInbox.setWithdrawalsEnabled(false)` | `onlyOwner` | **Owner Safe (3-of-5)** |
| 6 | Transfer Nock ownership | `Nock.transferOwnership` / `renounceOwnership` | `onlyOwner` | Owner Safe (3-of-5) |
| 7 | Transfer inbox ownership | `OwnableUpgradeable.transferOwnership` | `onlyOwner` | Owner Safe (3-of-5) |
| 8 | Change Safe owners/threshold | `Safe.addOwnerWithThreshold` / `swapOwner` / `changeThreshold` | Safe self-call (3-of-5) | Owner Safe (3-of-5) |
| — | Burn own NOCK for withdrawal | `Nock.burn(amount,lockRoot)` | holder balance only | **any holder** (permissionless, by design) |

### Powers **2, 3, 4** each independently give the Safe an unlimited mint
- **#4:** point `inbox` at an attacker-controlled contract → that contract calls `Nock.mint` freely.
- **#2:** upgrade the inbox implementation to one whose `submitDeposit`/any function mints without signatures.
- **#3:** replace 3 of the 5 signers with keys the Safe controls, then self-sign `submitDeposit`.

So **"3-of-5 of these keys" is the ceiling of trust for the whole token.** Compromise of 3 keys, by either the
bridge-signing path or the Safe path, yields unlimited NOCK and hence the pool's USDC.

## Authorities *outside* the bespoke system (bounded, non-NOCK)
| Authority | Address | Power | Scope |
|---|---|---|---|
| Aerodrome governance | `0xe6a41fe6…2075` (Safe) | `factory.pauser` / `feeManager` — can pause the pool or adjust its fee (capped) | Affects the pool, not NOCK mint. Canonical Aerodrome. |
| V2Locker owner | `0xb51ae43a…f294` (EOA) | withdraw the **49.6%** locked LP (lock **expired**) | Value owner; can pull its own liquidity, cannot mint/move NOCK. |
| Circle | USDC roles (masterMinter/blacklister/pauser) | standard FiatToken admin | Canonical USDC; out of NOCK's bespoke trust. |

## What an unprivileged address can do — nothing to the mint/admin surface
Verified empirically (from `0x…deadBeef`): every power 1–8 **reverts** for a non-authorized caller — `mint`
→ "Only inbox can mint"; `submitDeposit` with forged *or* valid non-node sigs → "Invalid signature(s)";
`updateInbox`/`updateBridgeNode`/`setWithdrawalsEnabled`/`upgradeToAndCall` → `OwnableUnauthorizedAccount`;
`notifyBurn` (spoof) → "Only Nock contract can notify burns"; `Safe.execTransaction` without quorum → revert.
Only the by-design-public actions (`burn` your own tokens, pool `swap`/`skim`) are reachable. See
[`05_simulation_results.md`](05_simulation_results.md).
