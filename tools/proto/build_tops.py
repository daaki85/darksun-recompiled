import sys,struct,collections
sys.path.insert(0,'/home/user/darksun-recompiled/tools'); sys.path.insert(0,'.')
import tops
from tops import *
src_dir=sys.argv[1]; out_dir=sys.argv[2]; NOSQUASH=len(sys.argv)>3 and sys.argv[3]=='nosquash'
_,O=s.load(f'{src_dir}/OBJEX.GFF'); _,C=s.load(f'{src_dir}/RGN032.GFF'); _,O0=s.load('/tmp/playtest/rav/OBJEX.GFF')
e=C[('ETAB',50)]; by=collections.defaultdict(list); _,C0=s.load('/tmp/playtest/rav/RGN032.GFF'); e0=C0[('ETAB',50)]
for k in range(len(e)//8):
    ob=abs(struct.unpack_from('<h',e,8*k+6)[0]); by[struct.unpack_from('<H',O[('OJFF',ob)],12)[0]].append(k)
tex=tiles(*OPTIONS['ashlar']); new={}
for pic,ents in by.items():
    if ('SCMD',pic) in O or pic in s.FLAT or ('BMP ',pic) not in O: continue
    raised=all(e0[8*k+4]>=30 for k in ents)
    c=O[('BMP ',pic)]; w,h,_=s.decode_any(c,0)
    if not raised and not (w<=24 or h>=56): continue   # furniture: no wall top
    tops.DROP=0 if (raised or NOSQUASH) else 16
    frames=[paint(s.decode_any(c,f)[2],w,h,tex) for f in range(s.frames(c)[0])]
    new[('BMP ',pic)]=s.picture(frames)
print(len(new),'pictures given SL tops')
s.append_chunks(f'{src_dir}/OBJEX.GFF',new,f'{out_dir}/OBJEX.GFF')
