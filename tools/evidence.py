#!/usr/bin/env python3
import rpc, json, urllib.request

BS="https://base.blockscout.com"
UA={"User-Agent":"Mozilla/5.0","Accept":"application/json"}
def bsget(path, params=None):
    url=BS+path
    if params: url+="?"+urllib.parse.urlencode(params)
    import urllib.parse
    req=urllib.request.Request(url, headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=40, context=rpc._CTX).read())

import urllib.parse

# 1) Locker INSTANCE (proxy) live state
INST="0x876B24D12608807AB76878b6CDCd4dD896BC2E48"
def c(a,sig,args=b""):
    r=rpc.try_call(a,sig,args); return r
print("=== V2Locker INSTANCE",INST,"(49.7% of pool LP) ===")
for fn in ["owner()","lockedUntil()","pool()","factory()"]:
    r=c(INST,fn)
    if r["ok"]:
        v=r["result"]
        if fn in("owner()","pool()","factory()"): print("  ",fn,"=",rpc.dec_addr(v))
        else:
            t=rpc.dec_uint(v)
            import datetime
            ds=datetime.datetime.utcfromtimestamp(t).isoformat()+"Z" if 0<t<2**32 else ("PERMANENT(max)" if t==2**32-1 else str(t))
            print("  ",fn,"=",t,"->",ds)
    else: print("  ",fn,"REVERT:",r["revert"])
lp=rpc.dec_uint(rpc.call("0x85f1aa3a70fedd1c52705c15baed143e675cd626","balanceOf(address)",rpc.enc_addr(INST)))
print("   LP held =",lp/1e18)

# 2) Nock InboxUpdated history -> was inbox ever a non-MessageInbox address (premine vector)?
print("\n=== Nock InboxUpdated history (premine / authority-rewiring evidence) ===")
try:
    logs=bsget("/api/v2/addresses/0x9b5e262cf9bb04869ab40b19af91d2dc85761722/logs")
    cnt={}
    for it in logs.get("items",[]):
        dec=it.get("decoded")
        nm=(dec or {}).get("method_call","") if dec else ""
        key=nm.split("(")[0] if nm else (it.get("topics",[None])[0] or "?")[:10]
        cnt[key]=cnt.get(key,0)+1
        if nm.startswith("InboxUpdated"):
            ps={p["name"]:p["value"] for p in dec["parameters"]}
            print("  InboxUpdated: old=",ps.get("oldInbox"),"new=",ps.get("newInbox"),"block",it.get("block_number"))
    print("  Nock event types (recent page):",cnt)
except Exception as e:
    print("  err",e)
