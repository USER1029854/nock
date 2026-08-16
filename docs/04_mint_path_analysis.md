# 04 · Mint-path analysis — `MessageInbox.submitDeposit`

The **only** way NOCK is minted. Source: [`../src/2-mint-authority/message-inbox-impl/MessageInbox.sol`](../src/2-mint-authority/message-inbox-impl/MessageInbox.sol).
This is a guard-by-guard read of the path plus the empirical confirmation from
[`05_simulation_results.md`](05_simulation_results.md).

## Signature / call flow

```solidity
function submitDeposit(Tip5Hash txId, Tip5Hash nameFirst, Tip5Hash nameLast,
                       address recipient, uint256 amount, uint256 blockHeight,
                       Tip5Hash asOf, uint256 depositNonce, bytes[] ethSigs) external {
    require(ethSigs.length >= 3, "Insufficient Ethereum signatures");     // THRESHOLD
    // Tip5 range checks: each of 5 limbs < 0xffffffff00000001 (Goldilocks prime)
    require(_isValidTip5(txId|nameFirst|nameLast|asOf));
    require(!_isZeroTip5(asOf), "Invalid as-of hash");
    require(amount > 0 && recipient != address(0));
    bytes32 txIdHash = keccak256(_encodeTip5(txId));                      // packed 5×uint64 = 40 bytes
    require(!processedDeposits[txIdHash], "Deposit already processed");   // REPLAY GUARD (per-txId)
    require(depositNonce > lastDepositNonce, "Nonce must be strictly greater");  // MONOTONIC GUARD
    require(_verifySignatures(_computeDepositHash(...), ethSigs), "Invalid Ethereum signatures");
    processedDeposits[txIdHash] = true;
    lastDepositNonce = depositNonce;
    nock.mint(recipient, amount);                                         // ← the mint
}
```

## Guards, one by one

| Guard | Mechanism | Assessment (mapping only, not a verdict) |
|---|---|---|
| **Caller** | none — `submitDeposit` is permissionless to *call* | Anyone can submit, but the mint requires signatures; simulation confirms an unprivileged submit reverts. |
| **Quorum** | `ethSigs.length >= 3`, then `_verifySignatures` counts **distinct** `bridgeNodes` via a `seen[5]` bitmap | Prevents one node signing 3×. Sig count is genuine 3-of-5 **membership**, proven empirically (valid non-node sigs are rejected). |
| **Signature scheme** | EIP-191 `personal_sign` over `keccak256(abi.encodePacked(txId,nameFirst,nameLast,recipient,amount,blockHeight,asOf,depositNonce))` | All fields fixed-size (Tip5 = 40 bytes packed; address 20; uints 32) → `encodePacked` has **no ambiguity/collision** surface here. Reconstructed independently and matched (see below). |
| **ECDSA malleability** | rejects `s > N/2` and `v ∉ {27,28}`; rejects `ecrecover == 0` | Canonical-signature enforcement present. |
| **Replay (per-deposit)** | `processedDeposits[keccak(txId)]` set before mint | Each Nockchain txId can mint once. Keyed on **txId only** (not the full tuple) — see note. |
| **Ordering** | `depositNonce > lastDepositNonce` strictly monotonic | Deposits must be submitted in increasing-nonce order; a stuck/oo-order nonce would block later ones until included. Operational coupling to the off-chain sequencer. |
| **Mint sink** | `nock.mint(recipient, amount)`; `Nock.mint` re-checks `msg.sender == inbox` | Belt-and-suspenders: even the inbox can only reach `_mint` via this path. |

## Notes for the audit (surface, not verdicts)
- **Amount is unbounded.** No per-deposit or cumulative cap; `amount` is whatever the signed tuple says. The
  only thing standing between a huge mint and reality is the honesty of the 3-of-5 signers and the off-chain
  machine that tells them what to sign (→ [`06_offchain_components.md`](06_offchain_components.md)).
- **`processedDeposits` is keyed on `txId` alone**, while the *signed* message binds the full tuple
  (recipient/amount/…). The audit may want to confirm the off-chain machine never issues two different tuples
  for one `txId` (the on-chain replay guard would treat them as the same deposit and only honor the first).
- **`asOf` causality hash** is range-checked and required non-zero but is **not** compared to any stored state
  on-chain — its meaning is enforced entirely off-chain.
- **`blockHeight`** is included in the signed message and emitted, but not validated on-chain.
- **Upgradeability caveat is closed by history:** because the inbox is UUPS, a *past* implementation could in
  principle have minted differently — but the proxy has **exactly one `Upgraded` event ever** (the constructor,
  to the current impl) and `inbox` has **exactly one `InboxUpdated` ever** (`0x0`→this proxy). So this exact
  `submitDeposit` logic is the only mint path that has **ever** existed. See [`07`](07_deposit_history_evidence.md).

## Independent verification of the signing scheme
`tools/simulate_mintpath.py` reconstructs the contract's `messageHash` from raw fields and signs it with three
throwaway keys. The contract accepted the signatures as well-formed (passed `recoverSigner`) and rejected them
only at **node membership** ("Invalid Ethereum signatures") — confirming (a) the message-hash layout above is
correct, and (b) the guard is membership in the 5-set, not mere signature validity.
