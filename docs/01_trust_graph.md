# 01 · Trust graph (both directions)

Resolved behaviorally — by following what the code actually reads, stores, calls, delegates to, sends value to,
and what holds authority over it — not by matching role names. Every hop was chased until the graph stopped
growing. All addresses below are on **Base (chainid 8453)**.

## Legend
- **▼ downstream** = what the target depends on (leans on)
- **▲ upstream** = what holds power over the target (can mint/move/reconfigure it)
- ✅ = verified source in this repo · 🔑 = off-chain key/component (see [`UNRESOLVED.md`](../UNRESOLVED.md))

---

## Target
- **Nock (NOCK)** `0x9b5e262cf9bb04869ab40b19af91d2dc85761722` ✅ — ERC20 (OZ v5.5.0) + Ownable, 16 decimals.
  Bespoke code is only `Nock.sol` (~2.8 KB): `mint(to,amount)` gated `msg.sender == inbox`;
  `burn(amount,lockRoot)` → `IMessageInbox(inbox).notifyBurn()`; `updateInbox(newInbox)` `onlyOwner`.

## ▼ Downstream — what Nock leans on

1. **`inbox` (live)** = `0x2033e72869c729b5a10f9c0a9d087c8297518021` ✅ — an **ERC1967 UUPS proxy**.
   - Reached because: `Nock.mint` requires `msg.sender == inbox`; `Nock.burn` calls `inbox.notifyBurn()`.
   - Resolved through the proxy to the **implementation** (live `eip1967.implementation` storage slot):
     **`0xcf6900c9fef4b3723856703e90a61d63a28dbe99`** = `MessageInbox` ✅. Admin slot = `0x0` → **UUPS**
     (upgrade authority lives in the implementation's `_authorizeUpgrade`, gated `onlyOwner`).
2. **`MessageInbox.nock` (live)** = `0x9b5e…1722` — back-reference to the target (bidirectional link confirmed).
3. **`MessageInbox.bridgeNodes[0..4]`** 🔑 — 5 EOAs whose signatures (3-of-5) authorize each mint. These are
   the leaves of the downstream graph (EOAs, no further code). Also the upstream root (see below).
4. **Aerodrome vAMM-USDC/NOCK pool** `0x85f1aa3a70fedd1c52705c15baed143e675cd626` — Nock is `token1` here.
   - The pool is a **45-byte EIP-1167 clone** of Aerodrome's canonical **Pool** impl
     `0xa4e46b4f701c62e14df11b48dce76a7d793cd6d7` ✅ (= `factory.implementation()`, verified live).
   - `token0` = **USDC** `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913` ✅ (canonical Circle FiatToken).
   - `factory` = **Aerodrome PoolFactory** `0x420dd381b31aef6683db6b902084cb0ffece40da` ✅ (fee/pause authority
     over the pool; `feeManager`=`pauser`=Aerodrome governance Safe `0xe6a4…2075`).

## ▲ Upstream — what holds power over Nock

1. **Owner Safe** `0xdc373766c03c645f04695224527ba7ef61fd4288` ✅ — **Gnosis Safe v1.4.1 (SafeL2)**, **3-of-5**.
   - Is `Nock.owner()` **and** `MessageInbox.owner()` (both confirmed live — one Safe owns both).
   - Powers: `Nock.updateInbox()` (repoint mint authority to any address); `MessageInbox.upgradeTo()` /
     `upgradeToAndCall()` (replace ALL mint logic — UUPS); `MessageInbox.updateBridgeNode()` (swap any of the 5
     signers); `MessageInbox.setWithdrawalsEnabled()` (brick burns).
   - Configuration (verified): singleton `0x29fcb43b46531bca003ddc8fcb67ffe91900c762` (canonical v1.4.1 SafeL2),
     fallback handler `0xfd0732…ec99` (canonical), **no modules**, **no guard**, threshold 3, nonce 1.
2. **`MessageInbox.bridgeNodes[0..4]`** 🔑 (3-of-5) — direct mint authority via `submitDeposit`.
3. **⇒ Collapse:** `Safe.getOwners()` returns **exactly the 5 bridgeNodes addresses**. The upstream graph's two
   branches are the **same 5 keys**. There is no separate admin key, no timelock, no separation of duties.

## Off-chain (in the trust path, no bytecode) 🔑
- **Nockchain→Base bridge / "Hoon state machine"** — computes the deposit tuples the 5 nodes sign. Named in
  `MessageInbox` comments. See [`06_offchain_components.md`](06_offchain_components.md) and [`UNRESOLVED.md`](../UNRESOLVED.md).

## Value owners (not authorities) — who holds the pooled USDC
Pro-rata LP holders of `0x85f1aa3a…`: **V2Locker** instance `0x876B24D1…2E48` ✅ (49.6%, lock expired
2026-06-22, owner `0xb51a…f294`), an **EIP-7702** smart-account EOA `0x078C…d4c9` (28.9%), EOA `0xdeb9…41a2`
(16.3%), remainder dust. These can withdraw **their own** liquidity; they cannot mint or move NOCK.

## Where the graph stops
Downstream ends at the 5 signer EOAs and canonical USDC. Upstream ends at the same 5 keys (via the Safe).
The pool/factory/USDC/locker are canonical or verified with no further bespoke authority over NOCK. No further
on-chain hops grow the graph. The only unresolved edges are **off-chain** (the keys and the Nockchain bridge).
