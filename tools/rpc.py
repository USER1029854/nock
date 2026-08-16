#!/usr/bin/env python3
"""Minimal Base RPC helper: eth_call, eth_getCode, storage, ABI encode/decode via keccak.
No external deps except pysha3/eth-hash fallback -> use hashlib keccak if available.
"""
import json, sys, os, ssl, urllib.request

RPCS = [
    "https://mainnet.base.org",
    "https://base-rpc.publicnode.com",
    "https://base.drpc.org",
    "https://base.meowrpc.com",
]

# Trust the agent-proxy CA so urllib works through the re-terminating proxy.
_CA = "/root/.ccr/ca-bundle.crt"
_CTX = ssl.create_default_context(cafile=_CA if os.path.exists(_CA) else None)
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

def rpc(method, params, rpc_url=None):
    body = json.dumps({"jsonrpc":"2.0","method":method,"params":params,"id":1}).encode()
    urls = [rpc_url] if rpc_url else RPCS
    last = None
    for u in urls:
        try:
            req = urllib.request.Request(u, data=body, headers={
                "Content-Type":"application/json","User-Agent":_UA,"Accept":"application/json"})
            r = json.loads(urllib.request.urlopen(req, timeout=40, context=_CTX).read())
            if "error" in r:
                last = r["error"]; continue
            return r["result"]
        except Exception as e:
            last = str(e); continue
    raise RuntimeError(f"RPC failed {method}: {last}")

# ---- keccak256 ----
try:
    from Crypto.Hash import keccak as _k
    def keccak(b):
        h=_k.new(digest_bits=256); h.update(b); return h.digest()
except Exception:
    # pure-python keccak fallback
    def keccak(b):
        return _keccak256(b)

def _keccak256(msg):
    # Minimal Keccak-256 implementation
    RC=[0x0000000000000001,0x0000000000008082,0x800000000000808A,0x8000000080008000,
        0x000000000000808B,0x0000000080000001,0x8000000080008081,0x8000000000008009,
        0x000000000000008A,0x0000000000000088,0x0000000080008009,0x000000008000000A,
        0x000000008000808B,0x800000000000008B,0x8000000000008089,0x8000000000008003,
        0x8000000000008002,0x8000000000000080,0x000000000000800A,0x800000008000000A,
        0x8000000080008081,0x8000000000008080,0x0000000080000001,0x8000000080008008]
    r=[[0]*5 for _ in range(5)]
    def rol(x,n): return ((x<<n)|(x>>(64-n)))&0xFFFFFFFFFFFFFFFF
    rate=136
    msg=bytearray(msg); msg.append(0x01)
    while len(msg)%rate!=0: msg.append(0)
    msg[-1]|=0x80
    for off in range(0,len(msg),rate):
        block=msg[off:off+rate]
        for i in range(rate//8):
            lane=int.from_bytes(block[i*8:i*8+8],'little')
            r[i%5][i//5]^=lane
        for rnd in range(24):
            C=[r[x][0]^r[x][1]^r[x][2]^r[x][3]^r[x][4] for x in range(5)]
            D=[C[(x-1)%5]^rol(C[(x+1)%5],1) for x in range(5)]
            for x in range(5):
                for y in range(5): r[x][y]^=D[x]
            B=[[0]*5 for _ in range(5)]
            rot=[[0,36,3,41,18],[1,44,10,45,2],[62,6,43,15,61],[28,55,25,21,56],[27,20,39,8,14]]
            for x in range(5):
                for y in range(5): B[y][(2*x+3*y)%5]=rol(r[x][y],rot[x][y])
            for x in range(5):
                for y in range(5): r[x][y]=B[x][y]^((~B[(x+1)%5][y])&B[(x+2)%5][y])
            r[0][0]^=RC[rnd]
    out=b''
    for i in range(rate//8):
        out+=int(r[i%5][i//5]).to_bytes(8,'little')
        if len(out)>=32: break
    return out[:32]

def selector(sig):
    return keccak(sig.encode())[:4]

def enc_addr(a):
    a=a.lower().replace("0x","")
    return bytes(12)+bytes.fromhex(a.rjust(40,'0'))

def enc_uint(n):
    return n.to_bytes(32,'big')

def call(to, sig, args_enc=b"", frm=None, block="latest"):
    data="0x"+(selector(sig)+args_enc).hex()
    p={"to":to,"data":data}
    if frm: p["from"]=frm
    return rpc("eth_call",[p, block])

def dec_addr(hexstr):
    h=hexstr.replace("0x","")
    return "0x"+h[-40:]

def dec_uint(hexstr):
    return int(hexstr,16) if hexstr not in ("0x","") else 0

def _decode_revert(data):
    if not data or data=="0x": return "(no revert data)"
    h=data[2:] if data.startswith("0x") else data
    if h[:8]=="08c379a0":  # Error(string)
        try:
            ln=int(h[8+64:8+128],16); return "Error: "+bytes.fromhex(h[8+128:8+128+ln*2]).decode("utf8","replace")
        except: return "Error(string) undecodable "+h
    if h[:8]=="4e487b71":  # Panic(uint256)
        return "Panic(0x%s)" % h[8+62:8+64]
    if h=="": return "(empty revert)"
    return "custom/selector 0x"+h[:8]

def try_call(to, sig, args_enc=b"", frm=None, value=None, block="latest"):
    """Returns dict: {ok, result?, revert?}. Uses eth_call; captures revert reason."""
    data="0x"+(selector(sig)+args_enc).hex()
    p={"to":to,"data":data}
    if frm: p["from"]=frm
    if value: p["value"]=hex(value)
    body=json.dumps({"jsonrpc":"2.0","method":"eth_call","params":[p,block],"id":1}).encode()
    last=None
    for u in RPCS:
        try:
            req=urllib.request.Request(u,data=body,headers={"Content-Type":"application/json","User-Agent":_UA})
            r=json.loads(urllib.request.urlopen(req,timeout=40,context=_CTX).read())
            if "error" in r:
                err=r["error"]; d=err.get("data")
                if isinstance(d,dict): d=d.get("data") or d.get("result")
                if isinstance(d,str) and d.startswith("0x"):
                    return {"ok":False,"revert":_decode_revert(d),"raw":d,"msg":err.get("message")}
                # some nodes put reason in message
                return {"ok":False,"revert":err.get("message",""),"raw":None,"msg":err.get("message")}
            return {"ok":True,"result":r["result"]}
        except Exception as e:
            last=str(e); continue
    return {"ok":False,"revert":"RPC-FAIL:"+str(last)}

if __name__=="__main__":
    # quick self-test
    print("keccak('') =", keccak(b"").hex())
    print("selector totalSupply() =", selector("totalSupply()").hex())
