#!/usr/bin/env python3
"""Deep mint-path probe: submit a deposit with 3 WELL-FORMED signatures from
random (non-bridge-node) keys, reproducing the contract's exact message hash.
Proves the guard is node-membership (3-of-5), not mere signature well-formedness."""
import rpc
from eth_account import Account
from eth_account.messages import encode_defunct

ATTACKER = "0x00000000000000000000000000000000deadBeef"
INBOX = "0x2033e72869c729b5a10f9c0a9d087c8297518021"

def pack_u64x5(vals): return b"".join(int(v).to_bytes(8,'big') for v in vals)
txId=[11,12,13,14,15]; nameFirst=[21,22,23,24,25]; nameLast=[31,32,33,34,35]; asOf=[41,42,43,44,45]
recipient=ATTACKER; amount=10**21; blockHeight=9999999; nonce=463

# Reproduce _computeDepositHash: keccak256(abi.encodePacked(...))
msg = (pack_u64x5(txId)+pack_u64x5(nameFirst)+pack_u64x5(nameLast)
       + bytes.fromhex(recipient[2:].rjust(40,'0'))
       + amount.to_bytes(32,'big') + blockHeight.to_bytes(32,'big')
       + pack_u64x5(asOf) + nonce.to_bytes(32,'big'))
messageHash = rpc.keccak(msg)
print("reconstructed messageHash =", "0x"+messageHash.hex())

# Sign the EIP-191 personal-sign digest with 3 random non-node keys
sigs=[]
for i in range(3):
    acct = Account.from_key(bytes([i+1])*32)  # deterministic random keys 0x0101..,0x0202..,0x0303..
    signed = acct.sign_message(encode_defunct(messageHash))
    r=signed.r.to_bytes(32,'big'); s=signed.s.to_bytes(32,'big'); v=bytes([signed.v])
    sigs.append(r+s+v)
    print(f"  signer{i} = {acct.address} (NOT a bridge node)  v={signed.v}")

def tip5(vals): return b"".join(rpc.enc_uint(x) for x in vals)
head  = tip5(txId)+tip5(nameFirst)+tip5(nameLast)+rpc.enc_addr(recipient)
head += rpc.enc_uint(amount)+rpc.enc_uint(blockHeight)+tip5(asOf)+rpc.enc_uint(nonce)
off=len(head)+32; head+=rpc.enc_uint(off)
tail=rpc.enc_uint(3); base=32*3; eo=b""; el=b""
for i,sig in enumerate(sigs):
    eo+=rpc.enc_uint(base+i*128); el+=rpc.enc_uint(65)+sig+b"\x00"*(96-65)
calldata=head+tail+eo+el

res = rpc.try_call(INBOX,
  "submitDeposit((uint64[5]),(uint64[5]),(uint64[5]),address,uint256,uint256,(uint64[5]),uint256,bytes[])",
  calldata, frm=ATTACKER)
print("\nsubmitDeposit(3 valid non-node sigs) from attacker ->",
      "REACHED/MINTED "+res.get("result","") if res["ok"] else "REVERTS: "+res["revert"])
