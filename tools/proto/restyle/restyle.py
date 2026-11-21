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
- The shift toward the party's mean is at most 15 lightness; a pale figure (its mean more than 10
  above the party's and little colour, chroma under 20: bone, white) moves only a quarter of the way, at most 8, keeping its brightness.
- The outline's darkening is chosen per figure so its edges come near the party's dark share (41%),
  and none added to a figure whose edges are already that dark.
- Quantised into WR's steady colours with a 2x2 ordered dither fixed to the frame's anchor (from the
  script's steps), so the pattern doesn't crawl as frames change.
- The script's per-frame anchors (step bytes 5, 6) scaled with the frames; movement isn't."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
HERE=os.path.dirname(os.path.abspath(__file__))
T=json.load(open(os.path.join(HERE,'party_target.json')))
K=0.82; MEAN_PULL=0.7; MAX_SHIFT=15.0; PALE=10.0; PALE_C=20.0; SAT=40.0; SAT_SHIFT=6.0; SAT_KEEP=0.85; EDGE_GOAL=0.41; MAX_DROP=5.0; MAX_DROP_DARK=13.0; PALE_PULL=0.1; PALE_MAX=4.0; KNEE=T['C_p90']; ABOVE=0.5; C_TARGET=45.0; EDGE_L=18.0
BAYER=np.array([[0.125,0.625],[0.875,0.375]])
_,ok=s.colour_table(SLPAL,s.wr_palettes('/tmp/playtest/rav'))
CAND=np.array(sorted(set(ok)|set(json.load(open(os.path.join(HERE,'wr_steady.json')))))); CLAB=WRLAB[CAND]   # with WR's 18 steady neutral greys
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
DEBUG=[]
ALL45=[693,716,1754,1755,1756,1757,1758,2345,2394,2403,2526,2537,2539,2554,2555,2556,2570,2843,2844,2845,2846,2847,2849,2850,2852,2853,2854,2855,2858,2859,2860,2861,2863,2884,2885,2887,2888,2889,2890,2891,2895,3461,3509,3866,1753]
def restyle_frames(frs, pic, combat, stats_from=None):
    small=[downscale(f) for f in frs]
    labs=np.concatenate([f[~np.isnan(f[...,0])] for f in small])
    mL,sdL=labs[:,0].mean(),max(labs[:,0].std(),1); C=np.hypot(labs[:,1],labs[:,2]); mC=max(C.mean(),1)
    pale=mL>T['L_mean']+PALE and mC<PALE_C; tsd=T['L_sd']
    if mC<PALE_C and abs(mL-T['L_mean'])>PALE:   # bone-white or obsidian-black: keep most of its own tone
        tmean=mL+float(np.clip(PALE_PULL*(T['L_mean']-mL),-PALE_MAX,PALE_MAX)); tsd=sdL   # and its own contrast
    elif mC>SAT:                                  # a colour variant (yellow, orange, red verini): keep its hue's lightness
        tmean=mL+float(np.clip(MEAN_PULL*(T['L_mean']-mL),-SAT_SHIFT,SAT_SHIFT))
    else:
        tmean=mL+float(np.clip(MEAN_PULL*(T['L_mean']-mL),-MAX_SHIFT,MAX_SHIFT))
    cscale=min(1.0,max(C_TARGET,SAT_KEEP*mC)/mC)  # toward 45 (a vivid figure keeps 85% of its colour)
    anc=anchors(pic,combat)
    # the colours: the steady set, plus every colour the figure's own art uses (its region shows them right)
    own=sorted(set(int(q) for f in frs for q in np.unique(f) if q>=0))
    cand=np.array(sorted(set(CAND.tolist())|set(own))); clab=WRLAB[cand]
    nonneutral=np.where(np.hypot(clab[:,1],clab[:,2])<6,0.0,1e6)
    # pass 1: each frame's toned lightness, colour and edges, before quantising
    work=[]
    for i,f in enumerate(small):
        m=~np.isnan(f[...,0]); H,W=m.shape
        if not m.any(): work.append(None); continue
        L=tmean+(f[...,0]-mL)*(tsd/sdL)
        a,b=f[...,1]*cscale,f[...,2]*cscale; c=np.hypot(a,b)
        capped=np.where(c>KNEE,KNEE+(c-KNEE)*ABOVE,c); r=np.where(c>0,capped/np.maximum(c,1e-6),1); a,b=a*r,b*r
        ys,xs=np.where(m); cx=(xs.min()+xs.max())/2; cy=(ys.min()+ys.max())/2
        X,Y=np.meshgrid(np.arange(W),np.arange(H))
        lr=np.nanmean(np.where(m&(X<cx),L,np.nan))-np.nanmean(np.where(m&(X>cx),L,np.nan))
        tb=np.nanmean(np.where(m&(Y<cy),L,np.nan))-np.nanmean(np.where(m&(Y>cy),L,np.nan))
        if np.isnan(lr): lr=T['lit_lr']
        if np.isnan(tb): tb=T['lit_tb']
        hw=max(1,(xs.max()-xs.min())/2); hh=max(1,(ys.max()-ys.min())/2)
        L=L+np.clip(T['lit_lr']-lr,-20,20)*(cx-X)/hw+np.clip(T['lit_tb']-tb,-20,20)*(cy-Y)/hh*0.5
        pad=np.pad(m,1)
        shade_edge=m&~(pad[2:,1:-1]&pad[1:-1,2:])            # clear below or to the right: the shadow side
        lit_edge=m&~(pad[:-2,1:-1]&pad[1:-1,:-2])&~shade_edge # clear above or to the left
        work.append((m,L,a,b,shade_edge,lit_edge,ys,xs))
    # the outline: the shadow side's darkening chosen so the edges come near the party's dark share
    # (41% below lightness 25), never darkening a figure whose edges are already that dark
    eL=np.concatenate([w[1][w[4]|w[5]] for w in work if w]); eS=np.concatenate([w[4][w[4]|w[5]] for w in work if w])
    base=(eL<19).mean() if len(eL) else 1
    allL=np.concatenate([w[1][w[0]] for w in work if w]); allE=np.concatenate([(w[4]|w[5])[w[0]] for w in work if w])
    allS=np.concatenate([w[4][w[0]] for w in work if w])
    fs=1.0
    if base<EDGE_GOAL:
        for f in np.arange(1.0,0.24,-0.05):
            dl=np.where(allS,allL*f,np.where(allE,allL*min(1,f+0.45),allL))
            if allL.mean()-dl.mean()>(MAX_DROP if pale else MAX_DROP_DARK): break      # a thin figure is mostly edge: keep its brightness
            fs=f
            if (dl[allE]<19).mean()>=EDGE_GOAL: break   # 19: dither lifts values near 25
    DEBUG.append((pic,combat,round(float(base),2),round(float(fs),2)))
    out=[]
    for i,(f,w) in enumerate(zip(small,work)):
        H,W=f.shape[:2]; res=np.full((H,W),-1)
        if not w: out.append(res); continue
        m,L,a,b,shade_edge,lit_edge,ys,xs=w
        L=np.where(shade_edge,L*fs,np.where(lit_edge,L*min(1,fs+0.45),L))
        Tlab=np.stack([np.clip(L,0,100),a,b],-1)
        ax,ay=anc.get(i,(W//2,H-1))
        for y,x in zip(ys,xs):
            d=((clab-Tlab[y,x])**2).sum(1)
            if np.hypot(Tlab[y,x,1],Tlab[y,x,2])<6: d=d+nonneutral      # a grey stays grey
            i1,i2=np.argsort(d)[:2]
            p,q=clab[i1],clab[i2]; seg=q-p; t=float(np.clip(((Tlab[y,x]-p)*seg).sum()/max((seg*seg).sum(),1e-6),0,1))
            res[y,x]=cand[i2] if BAYER[(y-ay)%2,(x-ax)%2]<t else cand[i1]
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
# People whose Shattered Lands match has the wrong shape (no legs, wrong build): restyled instead
# of dressed (people_dress.py leaves them out). Chosen by the owner, 2026-11-20.
PEOPLE=json.load(open(os.path.join(HERE,'..','people-restyle.json')))['restyle']
if __name__=='__main__':
    # restyle.py [--base OBJEX] [--out OBJEX] [--all45] [--people] [PICTURE ...]
    args=sys.argv[1:]; base,out='/tmp/playtest/rav/OBJEX.GFF','OBJEX_restyled.GFF'; pics=[]
    while args:
        a=args.pop(0)
        if a=='--base': base=args.pop(0)
        elif a=='--out': out=args.pop(0)
        elif a=='--all45': pics+=ALL45
        elif a=='--people': pics+=PEOPLE
        else: pics.append(int(a))
    new={}
    for p in pics: new.update(restyle(p)); print('restyled',p)
    s.write_ranged(base,new,out)
    _,R=s.load(out)
    for k in new:
        if k[0]!='SCMD':
            for f in range(s.frames(R[k])[0]): s.decode(R[k],f)
    print('written',out,'chunks',len(new))
