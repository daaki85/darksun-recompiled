import sys,struct,collections
sys.path.insert(0,'/home/user/darksun-recompiled/tools'); sys.path.insert(0,'.')
import sl_figures as s, gffw
from sl_figures import _lab as lab
DX,DY=12,8
_,O=s.load(sys.argv[1]); rgn=sys.argv[2]; out=sys.argv[3]
_,C=s.load(rgn); _,C0=s.load('/tmp/playtest/rav/RGN032.GFF'); e=C[('ETAB',50)]; e0=C0[('ETAB',50)]
pal=s.vga(C[('PAL ',50)]); gm=bytearray(C[('GMAP',50)])
cand=[j for j in range(32,256) if not 240<=j<=248]; cl={j:lab(pal[j]) for j in cand}
dark={}
def darker(q):
    if q not in dark:
        L=lab(pal[q]); t=(L[0]*0.55,L[1]*0.8,L[2]*0.8); dark[q]=min(cand,key=lambda j:sum((a-b)**2 for a,b in zip(t,cl[j])))
    return dark[q]
mask=collections.defaultdict(set)      # map-pixel shadow points
cover=collections.defaultdict(set)     # map pixels a structure itself covers (its shadow there unseen)
n=0
for k in range(len(e)//8):
    x,y,h,fl,ob=struct.unpack_from('<HHBBh',e,8*k); ob=abs(ob); oj=O[('OJFF',ob)]
    pic=struct.unpack_from('<H',oj,12)[0]; ax,ay=struct.unpack_from('<HH',oj,2)
    if ('SCMD',pic) in O or pic in s.FLAT or ('BMP ',pic) not in O: continue
    w,hh,px=s.decode_any(O[('BMP ',pic)],0)
    if not (w<=24 or hh>=56 or e0[8*k+4]>=30): continue          # structures only
    n+=1
    left=(x-896)-ax; top=(y+24)-h-ay
    for py,row in enumerate(px):
        for pxx,q in enumerate(row):
            if q is not None:
                X,Y=left+pxx+DX,top+py+DY
                mask[(X//16,Y//16)].add((X%16,Y%16))
                cover[((left+pxx)//16,(top+py)//16)].add(((left+pxx)%16,(top+py)%16))
tiles={i:v for (t,i),v in C.items() if t=='TILE'}
variants={}; nxt=max(tiles)+1; changes={}
def quarters(pts):
    q=0
    for b,(x0,y0) in enumerate(((0,0),(8,0),(0,8),(8,8))):
        if sum((x,y) in pts for x in range(x0,x0+8) for y in range(y0,y0+8))>=32: q|=1<<b
    return q
need=collections.Counter()
for (cx,cy),pts in list(mask.items()):
    vis=pts-cover.get((cx,cy),set()); qs=quarters(vis)
    if not qs or not (0<=cx<112 and 0<=cy<112): del mask[(cx,cy)]; continue
    mask[(cx,cy)]={(x,y) for b,(x0,y0) in enumerate(((0,0),(8,0),(0,8),(8,8))) if qs>>b&1 for x in range(x0,x0+8) for y in range(y0,y0+8)}
    need[(gm[cy*112+cx],qs)]+=1
print('visible shadowed cells',len(mask),'distinct (tile, quarters)',len(need))
for (cx,cy),pts in sorted(mask.items(), key=lambda kv:-need[(gm[kv[0][1]*112+kv[0][0]],quarters(kv[1]))]):
    if not (0<=cx<112 and 0<=cy<112): continue
    tid=gm[cy*112+cx]
    if tid not in tiles: continue
    key=(tid,frozenset(pts))
    if key not in variants:
        if nxt>255: continue
        w,hh,px=s.decode_any(tiles[tid],0)
        rows=[[darker(q) if (q is not None and (xx,yy) in pts) else q for xx,q in enumerate(r)] for yy,r in enumerate(px)]
        variants[key]=nxt; changes[('TILE',nxt)]=s.picture([rows]); nxt+=1
    gm[cy*112+cx]=variants[key]
changes[('GMAP',50)]=bytes(gm)
print(n,'structure entities;',len(mask),'cells touched;',len(variants),'new shadow tiles (ids up to',nxt-1,')')
gffw.write(rgn,changes,out)
