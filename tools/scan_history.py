#!/usr/bin/env python3
"""Robust full-range scan for authority-changing events on Nock + inbox proxy:
InboxUpdated (Nock) and Upgraded (proxy). Proper error handling so a complete
scan is provable (no silently-dropped windows)."""
import json, urllib.request, ssl, time, rpc
CTX=ssl.create_default_context(cafile='/root/.ccr/ca-bundle.crt')
URLS=['https://base.drpc.org','https://mainnet.base.org']
def call(method,params):
    body=json.dumps({'jsonrpc':'2.0','method':method,'params':params,'id':1}).encode()
    last=None
    for u in URLS:
        for attempt in range(3):
            try:
                req=urllib.request.Request(u,data=body,headers={'Content-Type':'application/json','User-Agent':'Mozilla/5.0'})
                r=json.loads(urllib.request.urlopen(req,timeout=55,context=CTX).read())
                if 'error' in r: last=r['error']; break
                return r['result']
            except Exception as e:
                last=str(e); time.sleep(1.5*(attempt+1))
    raise RuntimeError('getLogs failed: '+str(last))

def scan(addr, topic0, start, end, win=300000):
    ev=[]; b=start; windows=0; errors=0
    while b<=end:
        top=min(b+win,end)
        try:
            r=call('eth_getLogs',[{'address':addr,'topics':[topic0],'fromBlock':hex(b),'toBlock':hex(top)}])
            for l in r: ev.append((int(l['blockNumber'],16), l['topics'], l['transactionHash']))
        except Exception as e:
            errors+=1; print('   WINDOW ERROR',hex(b),hex(top),str(e)[:50])
        windows+=1; b=top+1
    return ev, windows, errors

NOCK='0x9b5e262cf9bb04869ab40b19af91d2dc85761722'
PROXY='0x2033e72869c729b5a10f9c0a9d087c8297518021'
tInbox='0x'+rpc.keccak(b'InboxUpdated(address,address)').hex()
tUpg='0x'+rpc.keccak(b'Upgraded(address)').hex()
start=39685409; end=int(rpc.rpc('eth_blockNumber',[]),16)
print(f'Scanning blocks {start}..{end} ({(end-start)/1e6:.1f}M blocks)')

ev,w,er=scan(NOCK,tInbox,start,end)
print(f'\nInboxUpdated: {len(ev)} events over {w} windows, {er} window-errors')
for b,tp,tx in ev: print(f'   block {b}: old=0x{tp[1][-40:]} new=0x{tp[2][-40:]}')

ev2,w2,er2=scan(PROXY,tUpg,start,end)
print(f'\nUpgraded(proxy impl): {len(ev2)} events over {w2} windows, {er2} window-errors')
for b,tp,tx in ev2: print(f'   block {b}: impl=0x{tp[1][-40:]}')
print('\nSCAN COMPLETE (errors must be 0 for a provably-complete scan):', 'CLEAN' if er==0 and er2==0 else f'{er+er2} ERRORS - rerun')
