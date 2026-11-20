"""Thick walls in a WR region, SL's way: every wall cell (GMAP 192: two cells wide, though WR draws
its walls as thin strips) that shows bare ground gets an SL ashlar top tile (the arena district's
tiles 5 and 43, in the region's palette), with a darker edge line where the wall meets open ground.
thickwalls.py RGN_IN RGN_OUT"""
import sys,collections
sys.path.insert(0,'/home/user/darksun-recompiled/tools'); sys.path.insert(0,'.')
import sl_figures as s, gffw
src,out=sys.argv[1:3]
_,C=s.load(src); pk=next(k for k in C if k[0]=='PAL '); pal=s.vga(C[pk])
mk=next(k for k in C if k[0] in('RMAP','MAP ')); m=bytearray(C[mk]); g=next(v for k,v in C.items() if k[0]=='GMAP')
_,A=s.load('/tmp/playtest/inst/RGN28.GFF'); _,GP=s.load('/tmp/playtest/inst/GPLDATA.GFF'); p40=s.vga(GP[('PAL ',0x28)])
cand=[j for j in range(32,256) if not 240<=j<=248]; cl={j:s._lab(pal[j]) for j in cand}
memo={}
def near(L):
    k=tuple(round(v) for v in L)
    if k not in memo: memo[k]=min(cand,key=lambda j:sum((a-b)**2 for a,b in zip(L,cl[j])))
    return memo[k]
tex=[[[s._lab(p40[q]) for q in r] for r in s.decode_any(A[('TILE',i)],0)[2]] for i in (5,43)]
wall=lambda c,r: 0<=c<128 and 0<=r<98 and g[r*128+c]==192
tiles={i for (t,i) in C if t=='TILE'}; nxt=max(tiles)+1; made={}; changes={}
for r in range(98):
    for c in range(128):
        if not wall(c,r): continue
        edges=(not wall(c,r-1),not wall(c+1,r),not wall(c,r+1),not wall(c-1,r))   # N E S W open
        key=((c+r)%2,edges)
        if key not in made:
            t=tex[key[0]]; rows=[]
            for y in range(16):
                row=[]
                for x in range(16):
                    L=list(t[y][x])
                    if (edges[0] and y==0) or (edges[1] and x==15) or (edges[2] and y==15) or (edges[3] and x==0):
                        L[0]*=0.55                       # the top's edge line
                    row.append(near(L))
                rows.append(row)
            made[key]=nxt; changes[('TILE',nxt)]=s.picture([rows]); nxt+=1
        m[r*128+c]=made[key]
changes[mk]=bytes(m)
print(sum(1 for r in range(98) for c in range(128) if wall(c,r)),'wall cells given ashlar tops;',len(made),'new tiles (to',nxt-1,')')
gffw.write(src,changes,out)
