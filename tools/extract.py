#!/usr/bin/env python3
"""Extract an Etherscan getsourcecode JSON into a directory tree of real files.
Handles standard-json-input ({{...}}), single-file, and multi-file formats.
Usage: extract.py <source_json> <outdir>
"""
import json, sys, os

def extract(src_json_path, outdir):
    d = json.load(open(src_json_path))
    r = d['result'][0]
    sc = r.get('SourceCode','')
    name = r.get('ContractName','Contract')
    os.makedirs(outdir, exist_ok=True)
    written = []
    if sc.startswith('{{'):
        obj = json.loads(sc[1:-1])
        for path, c in obj['sources'].items():
            fp = os.path.join(outdir, path)
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            open(fp,'w').write(c['content'])
            written.append(path)
        # save settings for compileability
        open(os.path.join(outdir,'_compiler_settings.json'),'w').write(
            json.dumps({'settings':obj.get('settings',{}),
                        'compiler':r.get('CompilerVersion'),
                        'evmVersion':r.get('EVMVersion'),
                        'optimizer':r.get('OptimizationUsed'),
                        'runs':r.get('Runs')}, indent=2))
    elif sc.startswith('{') and '"sources"' not in sc[:50] and 'content' not in sc[:200]:
        # rare single-brace multi-file
        obj = json.loads(sc)
        for path, c in obj.items():
            fp = os.path.join(outdir, path)
            os.makedirs(os.path.dirname(fp) or outdir, exist_ok=True)
            open(fp,'w').write(c['content'] if isinstance(c,dict) else c)
            written.append(path)
    else:
        fp = os.path.join(outdir, name + '.sol')
        open(fp,'w').write(sc)
        written.append(name+'.sol')
    return name, written

if __name__ == "__main__":
    name, files = extract(sys.argv[1], sys.argv[2])
    print(f"Extracted {name}: {len(files)} files -> {sys.argv[2]}")
    for f in files: print("  ", f)
