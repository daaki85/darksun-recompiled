import sys,struct,collections
sys.path.insert(0,'/home/user/darksun-recompiled/tools'); sys.path.insert(0,'.')
import sl_figures as s
from sl_figures import _lab as lab
DX,DY=10,6
src,rgn,out=sys.argv[1],sys.argv[2],sys.argv[3]
_,O=s.load(src); _,C=s.load(rgn); _,C0=s.load('/tmp/playtest/rav/RGN032.GFF')
pal=s.vga(C[('PAL ',50)]); e=C[('ETAB',50)]; e0=C0[('ETAB',50)]
cand=[j for j in range(32,256) if not 240<=j<=248]
SHADE=min(cand,key=lambda j:sum((a-b)**2 for a,b in zip(lab(pal[j]),(12,4,6))))   # near-black, a touch warm
by=collections.defaultdict(list)
for k in range(len(e)//8):
    ob=abs(struct.unpack_from('<h',e,8*k+6)[0]); by[struct.unpack_from('<H',O[('OJFF',ob)],12)[0]].append(k)
new={}
for pic,ents in by.items():
    if ('SCMD',pic) in O or pic in s.FLAT or ('BMP ',pic) not in O: continue
    c=O[('BMP ',pic)]; w,h,_=s.decode_any(c,0)
    if not (w<=24 or h>=56 or all(e0[8*k+4]>=30 for k in ents)): continue   # structures only
    frames=[]
    for f in range(s.frames(c)[0]):
        w,h,px=s.decode_any(c,f)
        W,H=w+DX,h+DY
        rows=[[None]*W for _ in range(H)]
        for y in range(h):
            for x in range(w):
                if px[y][x] is not None and (x+y)%2==0: rows[y+DY][x+DX]=SHADE   # the cast shadow, every other pixel
        for y in range(h):
            for x in range(w):
                if px[y][x] is not None: rows[y][x]=px[y][x]                    # the wall over it
        frames.append(rows)
    new[('BMP ',pic)]=s.picture(frames)
print(len(new),'structure pictures given a cast shadow; shade colour',SHADE,pal[SHADE])
s.append_chunks(src,new,out)
