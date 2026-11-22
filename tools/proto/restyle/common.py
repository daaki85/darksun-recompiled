import sys,json,struct
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import sl_figures as s
_,A=s.load('/tmp/playtest/sl_mod/SEGOBJEX.GFF'); _,B=s.load('/tmp/playtest/rav/OBJEX.GFF')
SLPAL=s.vga(s.load('/tmp/playtest/inst/GPLDATA.GFF')[1][('PAL ',1)])
WRPAL=s.vga(s.load('/tmp/playtest/rav/RGN032.GFF')[1][('PAL ',50)])
def lab_arr(rgb):
    a=np.asarray(rgb,float)/255.0; a=np.where(a>0.04045,((a+0.055)/1.055)**2.4,a/12.92)
    M=np.array([[0.4124,0.3576,0.1805],[0.2126,0.7152,0.0722],[0.0193,0.1192,0.9505]])
    xyz=a@M.T/np.array([0.95047,1,1.08883]); f=np.where(xyz>0.008856,np.cbrt(xyz),7.787*xyz+16/116)
    return np.stack([116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])],-1)
SLLAB=lab_arr(SLPAL); WRLAB=lab_arr(WRPAL)
def frames(C,t,p):
    c=C[(t,p)]; out=[]
    for f in range(s.frames(c)[0]):
        w,h,px=s.decode_any(c,f); out.append(np.array([[(-1 if q is None else q) for q in r] for r in px]))
    return out
