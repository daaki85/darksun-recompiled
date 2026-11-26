"""Draw a whole region of either game: ground (RMAP or MAP: 98 rows of 128 tiles) and placed objects
(ETAB, in rising y). SL region N in GPLDATA PAL N; WR in the region's own PAL."""
import sys,struct,os
sys.path.insert(0,'/home/user/darksun-recompiled/tools')
import sl_figures as s
from PIL import Image
_cache={}
def load(p):
    if p not in _cache: _cache[p]=s.load(p)[1]
    return _cache[p]
def draw(game, region, box=None, rgn_path=None, objex_path=None):
    if game=='SL':
        C=load(f'/tmp/playtest/inst/RGN{region:02X}.GFF'); O=load('/tmp/playtest/inst/SEGOBJEX.GFF')
        pal=s.vga(load('/tmp/playtest/inst/GPLDATA.GFF')[('PAL ',region)])
    else:
        C=load(rgn_path or f'/tmp/playtest/rav/RGN{region:03X}.GFF'); O=load(objex_path or '/tmp/playtest/rav/OBJEX.GFF')
        pal=s.vga(C[next(k for k in C if k[0]=='PAL ')])
    m=C[next(k for k in C if k[0] in ('RMAP','MAP '))]
    tiles={i:s.decode_any(v,0)[2] for (t,i),v in C.items() if t=='TILE'}
    x0,y0,W,H=box or (0,0,2048,1568)
    im=Image.new('RGB',(W,H))
    for r in range(y0//16,(y0+H)//16+1):
        for c in range(x0//16,(x0+W)//16+1):
            if not (0<=c<128 and 0<=r<98): continue
            px=tiles.get(m[r*128+c])
            if not px: continue
            for y,row in enumerate(px):
                for x,q in enumerate(row):
                    X,Y=c*16+x-x0,r*16+y-y0
                    if q is not None and 0<=X<W and 0<=Y<H: im.putpixel((X,Y),pal[q])
    ek=[k for k in C if k[0]=='ETAB']
    if ek:
        e=C[ek[0]]
        for x,y,h,fl,ob in sorted((struct.unpack_from('<HHBBh',e,8*k) for k in range(len(e)//8)),key=lambda t:t[1]):
            oj=O.get(('OJFF',abs(ob)))
            if not oj: continue
            pic=struct.unpack_from('<H',oj,12)[0]; ax,ay=struct.unpack_from('<HH',oj,2)
            if ('BMP ',pic) not in O: continue
            w,hh,px=s.decode_any(O[('BMP ',pic)],0); L,T=x-ax-x0,y-h-ay-y0
            if L>W or T>H or L+w<0 or T+hh<0: continue
            for yy,row in enumerate(px):
                for xx,q in enumerate(row):
                    if q is not None and 0<=L+xx<W and 0<=T+yy<H: im.putpixel((L+xx,T+yy),pal[q])
    return im
