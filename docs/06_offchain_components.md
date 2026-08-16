# 06 · Off-chain components in the trust path

These have **no bytecode to read and no address to simulate**. They cannot be resolved the way a contract is;
they can only be **named**, their controlled decision stated, and their behavior **bounded by on-chain evidence**.
They are the true root of trust — an off-chain component silently assumed honest is a hole exactly like an
unread contract. Full risk framing in [`../UNRESOLVED.md`](../UNRESOLVED.md).

## A. The 5 bridge-node signer keys 🔑 — the mint quorum

- **Addresses (EOAs):** `0x091f5a66…0964`, `0xcadeeee2…3f64`, `0x79a27406…b9cb`, `0xddde747a…0b3b`, `0xf0441e68…be76`
- **Decision they control:** which deposit tuples get 3-of-5 signatures → what NOCK is minted. They are *also*
  the Owner Safe's 5 owners, so they *also* decide upgrades / signer changes / inbox repointing.
- **If compromised (any 3):** unlimited NOCK → drain the ~315k USDC pool. No on-chain cap or timelock.
- **On-chain evidence of real behavior:**
  - All 5 are active EOAs (49–145 txs, 0.08–0.30 ETH each) — **operational hot wallets**, not cold multisig
    hardware. (`tools/simulate.py` characterization / live reads.)
  - They have authorized **462 deposits** over ~8 months with **strictly monotonic nonces**, to **181 distinct
    recipients**, in amounts consistent with a genuine token migration (max single ≈52.3 M NOCK; recent ≈12k–70k).
  - No observed mint of the entire supply to one sink; the pattern is many-small-deposits, not one-big-drain.
    (Full stats: [`07_deposit_history_evidence.md`](07_deposit_history_evidence.md).)
- **What the chain cannot show:** where the keys live, how they are generated/stored, whether any are
  co-located or share custody (correlated-compromise risk), or whether a threshold-signing/HSM scheme sits
  behind them. **Unresolvable from Base.**

## B. The Nockchain→Base bridge / "Hoon state machine" 🔑 — decides what is true

- **Named by the code itself** (`MessageInbox` comment): *"The off-chain Hoon state machine tracks deposits but
  cannot prevent replay because it is not the final arbiter of token minting — this contract is."* The naming of
  Nockchain state as **Tip5 hashes** (5×`uint64` Goldilocks-field limbs) and note **names** (`nameFirst`,
  `nameLast`) confirms an off-chain component that reads Nockchain and produces the tuples the nodes sign.
- **Decision it controls:** the mapping *real Nockchain deposit → Base mint instruction* (`txId, name*, amount,
  blockHeight, asOf`). **The Base contract verifies signatures, never the truth of the deposit.**
- **If wrong or compromised:** it can emit a tuple for a deposit that never happened; the 3-of-5 nodes sign it;
  the inbox mints **unbacked** NOCK. The on-chain token can be perfectly correct and still be inflated. This is
  the canonical bridge failure mode and the highest-leverage question for the audit.
- **On-chain evidence of real behavior:** the `DepositProcessed` log is the only window — it shows *what was
  signed* (462 deposits, monotonic nonce, plausible amounts/recipients) but **cannot** show whether each had
  genuine Nockchain backing. The `asOf` causality hash and `blockHeight` are carried in the signed message but
  **not checked on-chain**, so their integrity is entirely this component's responsibility.
- **Open questions:** How does the machine prove a Nockchain deposit to itself (light client vs. trusted
  indexer)? Is there redundancy/consensus among the 5 nodes' *views* of Nockchain, or do they all trust one
  feed? Who operates it?

## C. Nockchain-side withdrawal settlement 🔑

- **Decision it controls:** honoring a Base-side `burn(amount, lockRoot)` by releasing the corresponding
  Nockchain assets to `lockRoot`. Entirely off-chain.
- **If wrong/compromised:** burns un-honored (user loss) or double-honored. Does **not** drain the Base USDC
  pool, but is a user-fund risk in the bridge's trust path.
- **On-chain evidence:** the Base burn path is sound and observable — `withdrawalsEnabled == true`, `notifyBurn`
  correctly restricted to `msg.sender == nock`; the toggle is owner-only. The Nockchain settlement is not
  observable from Base.

## Why these belong in the audit even though they have no code
Reading only the token and walking outward through contracts would mark this system "clean" — every contract is
verified and every on-chain guard holds (see [`05`](05_simulation_results.md)). The realizable risk lives
precisely in A/B/C, which a contract-only reading never surfaces. They are recorded here as first-class,
evidence-bounded artifacts so the audit inherits them explicitly rather than by omission.
