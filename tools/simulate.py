#!/usr/bin/env python3
"""Empirical reachability: simulate value-path state-changing functions from an
arbitrary UNPRIVILEGED EOA against current Base mainnet state (eth_call).
Demonstrates what reverts (guarded) vs. what an unprivileged caller can reach."""
import rpc

ATTACKER = "0x00000000000000000000000000000000deadBeef"  # no roles anywhere
NOCK  = "0x9b5e262cf9bb04869ab40b19af91d2dc85761722"
INBOX = "0x2033e72869c729b5a10f9c0a9d087c8297518021"
POOL  = "0x85f1aa3a70fedd1c52705c15baed143e675cd626"

def show(label, res):
    if res["ok"]:
        print(f"  [REACHED]  {label}\n             -> returns {res['result']}")
    else:
        print(f"  [REVERTS]  {label}\n             -> {res['revert']}")

def tip5(a=1,b=2,c=3,d=4,e=5):
    # struct Tip5Hash { uint64[5] } -> static, 5 words inline
    return b"".join(rpc.enc_uint(x) for x in (a,b,c,d,e))

def build_submitDeposit(recipient, amount, nonce, nsigs=3):
    # submitDeposit((uint64[5]),(uint64[5]),(uint64[5]),address,uint256,uint256,(uint64[5]),uint256,bytes[])
    head  = tip5(11,12,13,14,15)          # txId
    head += tip5(21,22,23,24,25)          # nameFirst
    head += tip5(31,32,33,34,35)          # nameLast
    head += rpc.enc_addr(recipient)       # recipient
    head += rpc.enc_uint(amount)          # amount
    head += rpc.enc_uint(9999999)         # blockHeight
    head += tip5(41,42,43,44,45)          # asOf (nonzero, valid)
    head += rpc.enc_uint(nonce)           # depositNonce
    # ethSigs offset = size of head so far + 32 (for the offset word itself)
    off = len(head) + 32
    head += rpc.enc_uint(off)
    # tail: bytes[] = [len][off0..offN][elem0..elemN]
    tail = rpc.enc_uint(nsigs)
    # element offsets (relative to start after the length word)
    base = 32*nsigs
    elem_offsets = b""
    elems = b""
    for i in range(nsigs):
        elem_offsets += rpc.enc_uint(base + i*128)
        # signature: r(32)||s(32)||v(1) = 65 bytes; use distinct r, s=1, v=27
        r = (0x1111111111111111111111111111111111111111111111111111111111110000 + i).to_bytes(32,'big')
        s = (1).to_bytes(32,'big')
        v = (27).to_bytes(1,'big')
        sig = r+s+v
        elems += rpc.enc_uint(65) + sig + b"\x00"*(96-65)
    tail += elem_offsets + elems
    return head + tail

print("="*78)
print("UNPRIVILEGED-CALLER SIMULATION  (from", ATTACKER,")")
print("block", int(rpc.rpc("eth_blockNumber",[]),16))
print("="*78)

print("\n-- Target Nock: mint / burn / admin --")
show("Nock.mint(attacker, 1e21)  [attempt to mint out of thin air]",
    rpc.try_call(NOCK,"mint(address,uint256)", rpc.enc_addr(ATTACKER)+rpc.enc_uint(10**21), frm=ATTACKER))
show("Nock.updateInbox(attacker) [attempt to seize mint authority]",
    rpc.try_call(NOCK,"updateInbox(address)", rpc.enc_addr(ATTACKER), frm=ATTACKER))
show("Nock.burn(1e21, 0x..) [burn tokens attacker does not hold]",
    rpc.try_call(NOCK,"burn(uint256,bytes32)", rpc.enc_uint(10**21)+b"\x00"*32, frm=ATTACKER))

print("\n-- MessageInbox: the mint path & admin --")
show("MessageInbox.submitDeposit(...,3 forged sigs) [MINT PATH from attacker]",
    rpc.try_call(INBOX,
      "submitDeposit((uint64[5]),(uint64[5]),(uint64[5]),address,uint256,uint256,(uint64[5]),uint256,bytes[])",
      build_submitDeposit(ATTACKER, 10**21, 463), frm=ATTACKER))
show("MessageInbox.updateBridgeNode(0, attacker) [swap in attacker signer]",
    rpc.try_call(INBOX,"updateBridgeNode(uint256,address)", rpc.enc_uint(0)+rpc.enc_addr(ATTACKER), frm=ATTACKER))
show("MessageInbox.setWithdrawalsEnabled(false) [brick withdrawals]",
    rpc.try_call(INBOX,"setWithdrawalsEnabled(bool)", rpc.enc_uint(0), frm=ATTACKER))
show("MessageInbox.upgradeToAndCall(attacker, 0x) [replace mint logic]",
    rpc.try_call(INBOX,"upgradeToAndCall(address,bytes)", rpc.enc_addr(ATTACKER)+rpc.enc_uint(64)+rpc.enc_uint(0), frm=ATTACKER, value=0))
show("MessageInbox.notifyBurn() [spoof a burn notification, not from Nock]",
    rpc.try_call(INBOX,"notifyBurn()", b"", frm=ATTACKER))

print("\n-- Pool: swap reachability (normal user action, should be OPEN) --")
# skim() is permissionless on Aerodrome; just confirm pool is live/not paused via a view+state fn
show("Pool.skim(attacker) [permissionless housekeeping - expect reachable/no-op]",
    rpc.try_call(POOL,"skim(address)", rpc.enc_addr(ATTACKER), frm=ATTACKER))

print("\n-- Safe admin (3-of-5) --")
# execTransaction with empty sigs from attacker -> must revert (signature check)
show("Safe.execTransaction(attacker,0,0x,...,emptySigs) [admin action w/o quorum]",
    rpc.try_call("0xdc373766c03c645f04695224527ba7ef61fd4288",
      "execTransaction(address,uint256,bytes,uint8,uint256,uint256,uint256,address,address,bytes)",
      rpc.enc_addr(ATTACKER)+rpc.enc_uint(0)+rpc.enc_uint(320)  # data offset
      +rpc.enc_uint(0)+rpc.enc_uint(0)+rpc.enc_uint(0)+rpc.enc_uint(0)
      +rpc.enc_addr("0x0000000000000000000000000000000000000000")
      +rpc.enc_addr("0x0000000000000000000000000000000000000000")
      +rpc.enc_uint(384)  # sigs offset
      +rpc.enc_uint(0)    # data length 0
      +rpc.enc_uint(0),   # sigs length 0
      frm=ATTACKER))
