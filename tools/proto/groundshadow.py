"""Shattered Lands-style shadows drawn into a Ravager region's ground. Each structure's outline is cast
DX right and DY down (SL's light from the upper left) onto the ground map (MAP or RMAP: 98 rows of
128 tile numbers, tile (c, r) at map pixel (16c, 16r)); what any object covers is left out. Each
shadowed cell gets a copy of its tile, its shadowed pixels darkened as SL's shadowed floor is (the
pens' tile 26 against 28: lightness x 0.73, a + 11, b x 0.82), up to tile number 255.
groundshadow.py OBJEX RGN OUT_RGN [DX DY]"""
import sys,struct,collections
sys.path.insert(0,'/home/user/darksun-recompiled/tools'); sys.path.insert(0,'.')
import sl_figures as s, gffw
objex,rgn,out=sys.argv[1:4]
DX,DY=(int(sys.argv[4]),int(sys.argv[5])) if len(sys.argv)>5 else (12,8)
_,O=s.load(objex); _,C=s.load(rgn); _,C0=s.load('/tmp/playtest/rav/RGN032.GFF')
pk=next(k for k in C if k[0]=='PAL '); pal=s.vga(C[pk])
mk=next(k for k in C if k[0] in ('RMAP','MAP ')); gm=bytearray(C[mk]); W,H=128,98
ek=next(k for k in C if k[0]=='ETAB'); e=C[ek]; e0=C0[('ETAB',50)]
cand=[j for j in range(32,256) if not 240<=j<=248]; cl={j:s._lab(pal[j]) for j in cand}
dark={}
def darker(q):
    if q not in dark:
        L=s._lab(pal[q]); t=(L[0]*0.73,L[1]+11,L[2]*0.82)
        dark[q]=min(cand,key=lambda j:sum((a-b)**2 for a,b in zip(t,cl[j])))
    return dark[q]
shadow=collections.defaultdict(set); cover=collections.defaultdict(set); casters=0
for k in range(len(e)//8):
    x,y,h,fl,ob=struct.unpack_from('<HHBBh',e,8*k); oj=O.get(('OJFF',abs(ob)))
    if not oj: continue
    pic=struct.unpack_from('<H',oj,12)[0]; ax,ay=struct.unpack_from('<HH',oj,2)
    if ('BMP ',pic) not in O: continue
    w,hh,px=s.decode_any(O[('BMP ',pic)],0); left,top=x-ax,y-h-ay
    structure=('SCMD',pic) not in O and pic not in s.FLAT and (w<=24 or hh>=56 or e0[8*k+4]>=30)
    casters+=structure
    for yy,row in enumerate(px):
        for xx,q in enumerate(row):
            if q is None: continue
            X,Y=left+xx,top+yy
            cover[(X//16,Y//16)].add((X%16,Y%16))
            if structure:
                SX,SY=X+DX,Y+DY; shadow[(SX//16,SY//16)].add((SX%16,SY%16))
tiles={i:v for (t,i),v in C.items() if t=='TILE'}
cells={}
for cell,pts in shadow.items():
    c,r=cell
    if not (0<=c<W and 0<=r<H): continue
    vis=frozenset(pts-cover.get(cell,set()))
    if vis and gm[r*W+c] in tiles: cells[cell]=vis
need=collections.Counter((gm[r*W+c],v) for (c,r),v in cells.items())
budget=255-max(tiles)
print(casters,'structures cast shadows;',len(cells),'ground cells shadowed;',len(need),'distinct (tile, shadow) pairs; room for',budget)
def coarse(v,n):        # the shadow in n x n blocks (a block in shadow if half of it is)
    out=set()
    for bx in range(0,16,n):
        for by in range(0,16,n):
            if sum((x,y) in v for x in range(bx,bx+n) for y in range(by,by+n))*2>=n*n:
                out|={(x,y) for x in range(bx,bx+n) for y in range(by,by+n)}
    return frozenset(out)
cells={cell:coarse(v,8) for cell,v in cells.items()}; cells={k:v for k,v in cells.items() if v}
need=collections.Counter((gm[r*W+c],v) for (c,r),v in cells.items())
chosen=[k for k,_ in need.most_common(budget)]      # the most common (tile, shadow) pairs get tiles
by_tile=collections.defaultdict(list)
for tid,v in chosen: by_tile[tid].append(v)
ids={}; nxt=max(tiles)+1; changes={}
for tid,v in chosen:
    w,hh,px=s.decode_any(tiles[tid],0)
    rows=[[darker(q) if (q is not None and (x,y) in v) else q for x,q in enumerate(r)] for y,r in enumerate(px)]
    ids[(tid,v)]=nxt; changes[('TILE',nxt)]=s.picture([rows]); nxt+=1
exact=near=dropped=0
for (c,r),v in cells.items():
    tid=gm[r*W+c]
    if (tid,v) in ids: gm[r*W+c]=ids[(tid,v)]; exact+=1; continue
    best=max(by_tile.get(tid,[]),key=lambda u:len(u&v)/len(u|v),default=None)
    if best is not None and len(best&v)/len(best|v)>=0.5: gm[r*W+c]=ids[(tid,best)]; near+=1
    else: dropped+=1
print(f'{len(chosen)} shadow tiles (8-pixel blocks): {exact} cells exact, {near} the nearest shape, {dropped} left unshadowed; tiles {min(tiles)} to {nxt-1}')
changes[mk]=bytes(gm)
gffw.write(rgn,changes,out)
print('written',out,'tiles',min(tiles),'to',nxt-1)
