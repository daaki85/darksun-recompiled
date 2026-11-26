"""Rewrite a GFF whose index may be ranged (OBJEX.GFF, RESOURCE.GFF): chunks re-pointed or added,
the data appended, a new index written after it (the old index's trailing bytes kept)."""
import struct
def parse(d):
    toc,tlen=struct.unpack_from('<II',d,12); p=toc+8; n=struct.unpack_from('<H',d,p)[0]; p+=2; types=[]
    for _ in range(n):
        t=d[p:p+4]; c=struct.unpack_from('<I',d,p+4)[0]; p+=8
        if c&0x80000000:
            tot,gi,runs=struct.unpack_from('<III',d,p); rr=[list(struct.unpack_from('<II',d,p+12+8*k)) for k in range(runs)]
            types.append({'t':t,'ranged':True,'gi':gi,'runs':rr}); p+=12+8*runs
        else:
            types.append({'t':t,'ranged':False,'ents':[list(struct.unpack_from('<III',d,p+12*k)) for k in range(c)]}); p+=12*c
    return types, d[p:toc+tlen]
def write(path, changes, out):
    d=bytearray(open(path,'rb').read()); types,tail=parse(bytes(d))
    gffi=next(T for T in types if T['t']==b'GFFI')
    def gffi_ent(i): return next(e for e in gffi['ents'] if e[0]==i)
    idx={}                                  # ranged types: their id list and pair table
    for T in types:
        if T['ranged']:
            e=gffi_ent(T['gi']); raw=d[e[1]:e[1]+e[2]]
            ids=[i for f,n in T['runs'] for i in range(f,f+n)]
            pairs=[list(struct.unpack_from('<II',raw,4+8*k)) for k in range(len(ids))]
            idx[T['t']]=(T,ids,pairs)
    for (t,i),data in sorted(changes.items()):
        t=t.encode('latin1') if isinstance(t,str) else t
        at=len(d); d+=data
        if t in idx:
            T,ids,pairs=idx[t]
            if i in ids: pairs[ids.index(i)]=[at,len(data)]; continue
            if ids and i<ids[-1]: raise ValueError(f'new {t} id {i} must come after {ids[-1]}')
            if T['runs'] and T['runs'][-1][0]+T['runs'][-1][1]==i: T['runs'][-1][1]+=1
            else: T['runs'].append([i,1])
            ids.append(i); pairs.append([at,len(data)]); continue
        T=next((T for T in types if T['t']==t),None)
        ent=next((e for e in T['ents'] if e[0]==i),None) if T else None
        if ent: ent[1],ent[2]=at,len(data)
        else: raise ValueError(f'adding a chunk to plain type {t} not needed here')
    for t,(T,ids,pairs) in idx.items():     # each ranged type's offset table, rewritten
        raw=struct.pack('<I',len(pairs))+b''.join(struct.pack('<II',*p) for p in pairs)
        e=gffi_ent(T['gi']); e[1],e[2]=len(d),len(raw); d+=raw; T['total']=len(ids)
    body=bytearray(struct.pack('<H',len(types)))
    for T in types:
        if T['ranged']:
            body+=T['t']+struct.pack('<IIII',0x80000000|T['total'],T['total'],T['gi'],len(T['runs']))
            for r in T['runs']: body+=struct.pack('<II',*r)
        else:
            body+=T['t']+struct.pack('<I',len(T['ents']))
            for e in T['ents']: body+=struct.pack('<III',*e)
    body+=tail; toc=len(d); tlen=8+len(body)
    d+=struct.pack('<II',8,tlen-2)+body; struct.pack_into('<II',d,12,toc,tlen)
    open(out,'wb').write(d)
