import struct
def read_toc(d):
    toc,tlen=struct.unpack_from('<II',d,12); p=toc+8; n=struct.unpack_from('<H',d,p)[0]; p+=2; types=[]
    for _ in range(n):
        t=d[p:p+4]; c=struct.unpack_from('<I',d,p+4)[0]; p+=8
        if c&0x80000000: raise ValueError('ranged index not handled')
        types.append([t,[list(struct.unpack_from('<III',d,p+12*k)) for k in range(c)]]); p+=12*c
    return types, d[p:toc+tlen]
def write(path, changes, out):
    """PATH's GFF with CHANGES {(type4, id): bytes} applied: an existing chunk re-pointed to new data,
    a new one added to its type's list (or a new type). Data appended, a new index written after it."""
    d=bytearray(open(path,'rb').read()); types,tail=read_toc(bytes(d))
    for (t,i),data in changes.items():
        t=t.encode('latin1') if isinstance(t,str) else t
        at=len(d); d+=data
        ent=next((e for tt,es in types if tt==t for e in es if e[0]==i),None)
        if ent: ent[1],ent[2]=at,len(data); continue
        lst=next((es for tt,es in types if tt==t),None)
        if lst is None: lst=[]; types.append([t,lst])
        lst.append([i,at,len(data)]); lst.sort()
    body=bytearray(struct.pack('<H',len(types)))
    for t,es in types:
        body+=t+struct.pack('<I',len(es))
        for e in es: body+=struct.pack('<III',*e)
    body+=tail
    toc=len(d); tlen=8+len(body)
    d+=struct.pack('<II',8,tlen-2)+body
    struct.pack_into('<II',d,12,toc,tlen)
    open(out,'wb').write(d)
