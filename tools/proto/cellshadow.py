"""Shadows along a WR region's wall cells (GMAP 192), SL's way: each wall cell's square cast DX right
and DY down onto the open cells beside it (SL's light from the upper left), darkened as SL's shadowed
floor (lightness x 0.73, a + 11, b x 0.82). A cell's shadow depends only on whether its west, north
and north-west neighbours are walls, so the edges are straight and few tiles are needed.
cellshadow.py RGN_IN RGN_OUT [DX DY]"""
import sys,collections
sys.path.insert(0,'/home/user/darksun-recompiled/tools'); sys.path.insert(0,'.')
import sl_figures as s, gffw
src,out=sys.argv[1:3]; DX,DY=(int(sys.argv[3]),int(sys.argv[4])) if len(sys.argv)>4 else (12,8)
_,C=s.load(src); pk=next(k for k in C if k[0]=='PAL '); pal=s.vga(C[pk])
mk=next(k for k in C if k[0] in('RMAP','MAP ')); m=bytearray(C[mk]); g=next(v for k,v in C.items() if k[0]=='GMAP')
wall=lambda c,r: 0<=c<128 and 0<=r<98 and g[r*128+c]==192
cand=[j for j in range(32,256) if not 240<=j<=248]; cl={j:s._lab(pal[j]) for j in cand}
dark={}
def darker(q):
    if q not in dark:
        L=s._lab(pal[q]); t=(L[0]*0.73,L[1]+11,L[2]*0.82); dark[q]=min(cand,key=lambda j:sum((a-b)**2 for a,b in zip(t,cl[j])))
    return dark[q]
def mask(w,n,nw):
    """The shadow inside a cell: the west wall's square shifted (DX, DY) covers x < DX, y >= DY; the
    north wall's, x >= DX, y < DY; the north-west wall's, x < DX, y < DY."""
    return frozenset((x,y) for y in range(16) for x in range(16)
                     if (w and x<DX and y>=DY) or (n and x>=DX and y<DY) or (nw and x<DX and y<DY))
tiles={i:v for (t,i),v in C.items() if t=='TILE'}; nxt=max(tiles)+1; made={}; changes={}; n=0; skipped=0
for r in range(98):
    for c in range(128):
        if wall(c,r): continue
        w,nn,nw=wall(c-1,r),wall(c,r-1),wall(c-1,r-1)
        if not (w or nn or nw): continue
        tid=m[r*128+c]
        if tid not in tiles: continue
        msk=mask(w,nn,nw)
        if not msk: continue
        key=(tid,msk)
        if key not in made:
            if nxt>255: skipped+=1; continue
            px=s.decode_any(tiles[tid],0)[2]
            rows=[[darker(q) if (q is not None and (x,y) in msk) else q for x,q in enumerate(row)] for y,row in enumerate(px)]
            made[key]=nxt; changes[('TILE',nxt)]=s.picture([rows]); nxt+=1
        m[r*128+c]=made[key]; n+=1
changes[mk]=bytes(m)
print(n,'cells shadowed,',skipped,'left out for want of tile numbers;',len(made),'shadow tiles (to',nxt-1,')')
gffw.write(src,changes,out)
