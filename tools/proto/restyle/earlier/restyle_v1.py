"""Restyle Wake of the Ravager figure art into Shattered Lands' style, from measured style numbers
(style.json, measure.py): every frame scaled to SL's size (0.82: SL's human-sized figures stand 27
pixels against WR's 33), contrast raised to SL's (lightness spread x 1.29 about the figure's own
mean), colour lowered to SL's (chroma x 0.85), lit from the upper left (SL's left half is lighter),
edges darkened toward SL's outline share, and quantised with a 2 x 2 ordered dither between the two
nearest colours (SL figures are twice as dithered: 43% of interior pixels alternate against WR's
21%), into the colours WR keeps steady (sl_figures.colour_table). The scripts' per-frame anchors
(step bytes 5, 6) are scaled with the frames; the steps' movement (bytes 3, 4) is not."""
from common import *
K=0.82; CONTRAST=18.67/14.47; CHROMA=28.53/33.66; LIGHT_LR=3.0; LIGHT_TB=1.0; EDGE=0.80
BAYER=np.array([[0.125,0.625],[0.875,0.375]])
_,ok=s.colour_table(SLPAL,s.wr_palettes('/tmp/playtest/rav'))
CAND=np.array(ok); CLAB=WRLAB[CAND]
def downscale(fr):
    h,w=fr.shape; H,W=max(1,round(h*K)),max(1,round(w*K)); out=np.full((H,W),-1)
    for Y in range(H):
        y0,y1=int(Y/K),max(int(Y/K)+1,int((Y+1)/K))
        for X in range(W):
            x0,x1=int(X/K),max(int(X/K)+1,int((X+1)/K))
            box=fr[y0:y1,x0:x1]; m=box>=0
            if m.mean()<0.5: continue
            q=box[m]; L=WRLAB[q]; mu=L.mean(0)
            dark=L[:,0]<20
            if dark.mean()>=1/3: out[Y,X]=q[dark][0]; continue      # keep thin dark lines
            out[Y,X]=q[np.argmin(((L-mu)**2).sum(1))]
    return out
def restyle_frames(frs):
    small=[downscale(f) for f in frs]
    allL=np.concatenate([WRLAB[f[f>=0]][:,0] for f in small if (f>=0).any()]); mL=allL.mean()
    out=[]
    for f in small:
        m=f>=0; H,W=f.shape; res=np.full((H,W),-1)
        if not m.any(): out.append(res); continue
        lab=WRLAB[np.clip(f,0,255)].copy()
        ys,xs=np.where(m); cx=(xs.min()+xs.max())/2; cy=(ys.min()+ys.max())/2; hw=max(1,(xs.max()-xs.min())/2); hh=max(1,(ys.max()-ys.min())/2)
        X,Y=np.meshgrid(np.arange(W),np.arange(H))
        L=mL+(lab[...,0]-mL)*CONTRAST+LIGHT_LR*(cx-X)/hw+LIGHT_TB*(cy-Y)/hh
        pad=np.pad(m,1); edge=m&~(pad[:-2,1:-1]&pad[2:,1:-1]&pad[1:-1,:-2]&pad[1:-1,2:])
        L=np.where(edge,L*EDGE,L)
        T=np.stack([np.clip(L,0,100),lab[...,1]*CHROMA,lab[...,2]*CHROMA],-1)
        for y,x in zip(ys,xs):
            d=((CLAB-T[y,x])**2).sum(1); i1,i2=np.argsort(d)[:2]
            a,b=CLAB[i1],CLAB[i2]; seg=b-a; t=float(np.clip(((T[y,x]-a)*seg).sum()/max((seg*seg).sum(),1e-6),0,1))
            res[y,x]=CAND[i2] if BAYER[y%2,x%2]<t else CAND[i1]
        out.append(res)
    return out
def chunk(frs):
    return s.picture([[[None if q<0 else int(q) for q in row] for row in f] for f in frs])
def script(sc):
    out=bytearray(sc)
    for k in range((len(sc)-72)//8):
        at=72+8*k; out[at+5]=round(sc[at+5]*K); out[at+6]=round(sc[at+6]*K)
    return bytes(out)
def restyle(pic):
    new={}
    for t in ('BMP ','CBMP'):
        if (t,pic) in B: new[(t,pic)]=chunk(restyle_frames(frames(B,t,pic)))
    if ('SCMD',pic) in B: new[('SCMD',pic)]=script(B[('SCMD',pic)])
    return new
if __name__=='__main__':
    pics=[int(a) for a in sys.argv[1:]]
    new={}
    for p in pics: new.update(restyle(p)); print('restyled',p)
    s.write_ranged('/tmp/playtest/rav/OBJEX.GFF',new,'OBJEX_restyled.GFF')
    _,R=s.load('OBJEX_restyled.GFF')
    for k in new:
        if k[0]!='SCMD':
            for f in range(s.frames(R[k])[0]): s.decode(R[k],f)
    print('written OBJEX_restyled.GFF, chunks',len(new))
