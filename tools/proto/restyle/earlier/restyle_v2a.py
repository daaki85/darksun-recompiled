"""Restyle Wake of the Ravager figure art into Shattered Lands' style (v2: tuned to the mod's party
figures as drawn in WR's colours, the creatures' actual neighbours; party_target.json).
- Scale 0.82 (SL's human-sized figures 27 px against WR's 33), each new pixel the coverage-weighted
  Lab average of its block (thin patterns and stripes blend instead of aliasing), thin dark lines kept.
- Tone: the party's lightness spread (sd 19.9) and 70% of the way to its mean (30); chroma toward 45
  (the party's mean is 30: a strongly coloured creature keeps its identifying hues), half the excess
  above the party's 90th percentile (54) kept.
- Light: per frame, a linear ramp that turns the frame's lit side to the party's (left half 4.2
  lighter, top 7.2 lighter), whatever side WR lit.
- Outline: SL's light from the upper left: edges on the shadow side (clear below or to the right)
  darkened (x 0.55), lit edges a little (x 0.9); a neutral pixel is dithered among neutral greys only (the party: 41% of edge pixels below lightness 25).
- The shift toward the party's mean is at most 15 lightness (a skeleton stays light).
- Quantised into WR's steady colours with a 2x2 ordered dither fixed to the frame's anchor (from the
  script's steps), so the pattern doesn't crawl as frames change.
- The script's per-frame anchors (step bytes 5, 6) scaled with the frames; movement isn't."""
from common import *
T=json.load(open('party_target.json'))
K=0.82; MEAN_PULL=0.7; MAX_SHIFT=15.0; KNEE=T['C_p90']; ABOVE=0.5; C_TARGET=45.0; EDGE_L=18.0
BAYER=np.array([[0.125,0.625],[0.875,0.375]])
_,ok=s.colour_table(SLPAL,s.wr_palettes('/tmp/playtest/rav'))
CAND=np.array(sorted(set(ok)|set(json.load(open('wr_steady.json'))))); CLAB=WRLAB[CAND]   # with WR's 18 steady neutral greys
NONNEUTRAL=np.where(np.hypot(CLAB[:,1],CLAB[:,2])<6,0.0,1e6)
def downscale(fr):
    """(Lab rows with NaN where clear, the dark-line mask) at K."""
    h,w=fr.shape; H,W=max(1,round(h*K)),max(1,round(w*K)); out=np.full((H,W,3),np.nan)
    for Y in range(H):
        y0,y1=int(Y/K),max(int(Y/K)+1,int((Y+1)/K))
        for X in range(W):
            x0,x1=int(X/K),max(int(X/K)+1,int((X+1)/K))
            box=fr[y0:y1,x0:x1]; m=box>=0
            if m.mean()<0.5: continue
            L=WRLAB[box[m]]; dark=L[:,0]<20
            out[Y,X]=L[dark].mean(0) if dark.mean()>=1/3 else L.mean(0)
    return out
def anchors(pic, combat):
    sc=B.get(('SCMD',pic)); out={}
    if not sc: return out
    for k in range((len(sc)-72)//8):
        st=sc[72+8*k:80+8*k]
        if bool(st[2]&0x20)==combat and st[0] not in out: out[st[0]]=(round(st[5]*K),round(st[6]*K))
    return out
def restyle_frames(frs, pic, combat, stats_from=None):
    small=[downscale(f) for f in frs]
    labs=np.concatenate([f[~np.isnan(f[...,0])] for f in small])
    mL,sdL=labs[:,0].mean(),max(labs[:,0].std(),1); C=np.hypot(labs[:,1],labs[:,2]); mC=max(C.mean(),1)
    tmean=mL+float(np.clip(MEAN_PULL*(T['L_mean']-mL),-MAX_SHIFT,MAX_SHIFT)); cscale=min(1.0,C_TARGET/mC)   # toward 45, not the party's 30: a creature's own colours stay recognisable
    anc=anchors(pic,combat); out=[]
    for i,f in enumerate(small):
        m=~np.isnan(f[...,0]); H,W=m.shape; res=np.full((H,W),-1)
        if not m.any(): out.append(res); continue
        L=tmean+(f[...,0]-mL)*(T['L_sd']/sdL)
        a,b=f[...,1]*cscale,f[...,2]*cscale; c=np.hypot(a,b)
        capped=np.where(c>KNEE,KNEE+(c-KNEE)*ABOVE,c); r=np.where(c>0,capped/np.maximum(c,1e-6),1); a,b=a*r,b*r
        ys,xs=np.where(m); cx=(xs.min()+xs.max())/2; cy=(ys.min()+ys.max())/2
        X,Y=np.meshgrid(np.arange(W),np.arange(H))
        lr=np.nanmean(np.where(m&(X<cx),L,np.nan))-np.nanmean(np.where(m&(X>cx),L,np.nan))
        tb=np.nanmean(np.where(m&(Y<cy),L,np.nan))-np.nanmean(np.where(m&(Y>cy),L,np.nan))
        if np.isnan(lr): lr=T['lit_lr']
        if np.isnan(tb): tb=T['lit_tb']
        hw=max(1,(xs.max()-xs.min())/2); hh=max(1,(ys.max()-ys.min())/2)
        L=L+np.clip(T['lit_lr']-lr,-20,20)*(cx-X)/hw/1.0*0.5*2+np.clip(T['lit_tb']-tb,-20,20)*(cy-Y)/hh*0.5
        pad=np.pad(m,1)
        shade_edge=m&~(pad[2:,1:-1]&pad[1:-1,2:])            # clear below or to the right: the shadow side
        lit_edge=m&~(pad[:-2,1:-1]&pad[1:-1,:-2])&~shade_edge # clear above or to the left
        L=np.where(shade_edge,L*0.55,np.where(lit_edge,L*0.9,L))
        Tlab=np.stack([np.clip(L,0,100),a,b],-1)
        ax,ay=anc.get(i,(W//2,H-1))
        for y,x in zip(ys,xs):
            d=((CLAB-Tlab[y,x])**2).sum(1)
            if np.hypot(Tlab[y,x,1],Tlab[y,x,2])<6: d=d+NONNEUTRAL      # a grey stays grey
            i1,i2=np.argsort(d)[:2]
            p,q=CLAB[i1],CLAB[i2]; seg=q-p; t=float(np.clip(((Tlab[y,x]-p)*seg).sum()/max((seg*seg).sum(),1e-6),0,1))
            res[y,x]=CAND[i2] if BAYER[(y-ay)%2,(x-ax)%2]<t else CAND[i1]
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
    for t,combat in (('BMP ',False),('CBMP',True)):
        if (t,pic) in B: new[(t,pic)]=chunk(restyle_frames(frames(B,t,pic),pic,combat))
    if ('SCMD',pic) in B: new[('SCMD',pic)]=script(B[('SCMD',pic)])
    return new
if __name__=='__main__':
    pics=[int(a) for a in sys.argv[1:]]; new={}
    for p in pics: new.update(restyle(p)); print('restyled',p)
    s.write_ranged('/tmp/playtest/rav/OBJEX.GFF',new,'OBJEX_restyled.GFF')
    _,R=s.load('OBJEX_restyled.GFF')
    for k in new:
        if k[0]!='SCMD':
            for f in range(s.frames(R[k])[0]): s.decode(R[k],f)
    print('written OBJEX_restyled.GFF, chunks',len(new))
