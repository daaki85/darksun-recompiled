import sys,struct
sys.path.insert(0,'/home/user/darksun-recompiled/tools'); sys.path.insert(0,'.')
import sl_figures as s
from sl_figures import _lab as lab
from PIL import Image, ImageDraw
_,G=s.load('/tmp/playtest/inst/GPLDATA.GFF')
_,T=s.load('/tmp/playtest/ravsl/RGN032.GFF'); tpal=s.vga(T[('PAL ',50)])
cand=[j for j in range(32,256) if not 240<=j<=248]; clab={j:lab(tpal[j]) for j in cand}
memo={}
def near(L):
    k=tuple(round(v) for v in L)
    if k not in memo: memo[k]=min(cand,key=lambda j:sum((a-b)**2 for a,b in zip(L,clab[j])))
    return memo[k]
def tiles(region,ids):
    _,C=s.load(f'/tmp/playtest/inst/RGN{region:02X}.GFF'); pal=s.vga(G[('PAL ',region)])
    return [[[lab(pal[q]) if q is not None else None for q in row] for row in s.decode_any(C[('TILE',i)],0)[2]] for i in ids]
OPTIONS={'ashlar':(0x28,[5,43]),'brick':(0x29,[2,3]),'rubble':(0x29,[57,58])}
FACE,DROP=48,16
def top_rows(w,h):
    if w<=24: return range(0,h)            # a thin piece (a wall running away): all of it is wall top
    if h<=FACE: return None
    return range(DROP, DROP+(h-FACE))      # where the top band sits after the squash
def paint(px, w, h, tex):
    """PX (squashed picture rows) with its top band refilled from TEX (tiles in Lab), aligned on 16."""
    rows=top_rows(w,h)
    if not rows: return px
    seen=[lab(tpal[px[y][x]]) for y in rows for x in range(w) if px[y][x] is not None]
    if seen and sum(1 for L in seen if L[1]>25 and L[1]>L[2])>0.3*len(seen):
        return px                          # a roofed wall: its top is WR's roof tiles, kept
    out=[list(r) for r in px]; band=set()
    for y in rows:
        for x in range(w):
            q=px[y][x]
            if q is None: continue
            L=lab(tpal[q])
            if L[0]<22 or (L[1]>25 and L[1]>L[2]):   # dark details and red roof tiles stay WR's
                continue
            t=tex[(x//16)%len(tex)][(y-rows.start)%16][x%16]
            if t is None: continue
            band.add((x,y)); out[y][x]=near(t)
    for (x,y) in band:                     # a darker line round the band's outer edge
        edge=any((x+dx,y+dy) not in band and 0<=x+dx<w and 0<=y+dy<h and (px[y+dy][x+dx] is None or y+dy<rows.start) for dx,dy in ((1,0),(-1,0),(0,-1)))
        if edge or y==rows.start:
            L=list(clab[out[y][x]]); L[0]*=0.6; out[y][x]=near(L)
    return out
