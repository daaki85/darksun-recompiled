"""Cast shadows baked into Tyr's structure pictures in one global checkerboard: a shadow pixel only
where its screen x + y is even, so overlapping shadows stay a checkerboard. A picture placed at both
pixel parities gets a copy with the other phase (BMP 5001 on), its odd placements a copy of their
object pointing at it (OJFF 32100 on)."""
import sys,struct,collections
sys.path.insert(0,'/home/user/darksun-recompiled/tools'); sys.path.insert(0,'.')
import sl_figures as s, gffr
from sl_figures import _lab as lab
DX,DY=10,6
src,rgn,out_obj,out_rgn=sys.argv[1:5]
_,O=s.load(src); _,C=s.load(rgn); _,C0=s.load('/tmp/playtest/rav/RGN032.GFF')
pal=s.vga(C[('PAL ',50)]); e=bytearray(C[('ETAB',50)]); e0=C0[('ETAB',50)]
cand=[j for j in range(32,256) if not 240<=j<=248]
SHADE=min(cand,key=lambda j:sum((a-b)**2 for a,b in zip(lab(pal[j]),(12,4,6))))
inst=collections.defaultdict(list)          # picture -> [(entity, object, parity)]
for k in range(len(e)//8):
    x,y,h,fl,ob=struct.unpack_from('<HHBBh',e,8*k); ob=abs(ob); oj=O[('OJFF',ob)]
    pic=struct.unpack_from('<H',oj,12)[0]; ax,ay=struct.unpack_from('<HH',oj,2)
    if ('SCMD',pic) in O or pic in s.FLAT or ('BMP ',pic) not in O: continue
    w,hh,_=s.decode_any(O[('BMP ',pic)],0)
    if not (w<=24 or hh>=56 or e0[8*k+4]>=30): continue
    inst[pic].append((k,ob,((x-ax)+(y-h-ay))%2))
def baked(c,phase):
    frames=[]
    for f in range(s.frames(c)[0]):
        w,h,px=s.decode_any(c,f); W,H=w+DX,h+DY
        rows=[[None]*W for _ in range(H)]
        for y in range(h):
            for x in range(w):
                if px[y][x] is not None and (x+DX+y+DY+phase)%2==0: rows[y+DY][x+DX]=SHADE
        for y in range(h):
            for x in range(w):
                if px[y][x] is not None: rows[y][x]=px[y][x]
        frames.append(rows)
    return s.picture(frames)
changes={}; next_pic=5001; next_obj=32100; copies={}
for pic,lst in sorted(inst.items()):
    phases={p for _,_,p in lst}; c=O[('BMP ',pic)]
    base=min(phases); changes[('BMP ',pic)]=baked(c,base)
    if len(phases)==1: continue
    changes[('BMP ',next_pic)]=baked(c,1-base)
    for k,ob,p in lst:
        if p==base: continue
        if ob not in copies:
            oj=bytearray(O[('OJFF',ob)]); struct.pack_into('<H',oj,12,next_pic)
            changes[('OJFF',next_obj)]=bytes(oj); copies[ob]=next_obj; next_obj+=1
        struct.pack_into('<h',e,8*k+6,-copies[ob])
    next_pic+=1
print(len(inst),'pictures shadowed;',next_pic-5001,'odd-phase copies;',len(copies),'object copies (32100 to',next_obj-1,')')
gffr.write(src,changes,out_obj)
s.append_chunks(rgn,{('ETAB',50):bytes(e)},out_rgn)
