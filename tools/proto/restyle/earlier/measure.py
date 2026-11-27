from common import *
def stats(fr,LAB):
    m=fr>=0
    if m.sum()<20: return None
    ys,xs=np.where(m); h=ys.max()-ys.min()+1; w=xs.max()-xs.min()+1
    L=np.where(m,LAB[np.clip(fr,0,255)][...,0],np.nan); ab=LAB[np.clip(fr,0,255)][...,1:]
    C=np.hypot(ab[...,0],ab[...,1])
    pad=np.pad(m,1); edge=m&~(pad[:-2,1:-1]&pad[2:,1:-1]&pad[1:-1,:-2]&pad[1:-1,2:])
    inter=m&~edge
    Le=L[edge]; Li=L[inter] if inter.any() else L[m]
    d2=L[:,1:-1]-L[:,:-2]; d3=L[:,2:]-L[:,1:-1]; ok=~np.isnan(d2*d3)&inter[:,1:-1]
    checker=float(((d2*d3)<-25)[ok].mean()) if ok.any() else 0
    cx=(xs.min()+xs.max())/2; cy=(ys.min()+ys.max())/2
    left=np.nanmean(L[m&(np.arange(fr.shape[1])[None,:]<cx)]); right=np.nanmean(L[m&(np.arange(fr.shape[1])[None,:]>cx)])
    top=np.nanmean(L[m&(np.arange(fr.shape[0])[:,None]<cy)]); bot=np.nanmean(L[m&(np.arange(fr.shape[0])[:,None]>cy)])
    cols=np.unique(fr[m])
    # shades: distinct lightness levels per hue group (hue in 30-degree bins, chroma>8; greys their own group)
    hue=np.degrees(np.arctan2(ab[...,1],ab[...,0]))%360
    grp={}
    for q in cols:
        a,b=LAB[q][1],LAB[q][2]; c=np.hypot(a,b); key='grey' if c<8 else int((np.degrees(np.arctan2(b,a))%360)//30)
        grp.setdefault(key,[]).append(LAB[q][0])
    big=[sorted(v) for v in grp.values() if len(v)>=3]
    shades=np.mean([len(v) for v in big]) if big else 0
    step=np.mean([np.mean(np.diff(v)) for v in big]) if big else 0
    return dict(h=h,w=w,edge_dark=float((Le<25).mean()),edge_L=float(np.nanmean(Le)),inner_L=float(np.nanmean(Li)),
                L_sd=float(np.nanstd(L[m])),L_p5=float(np.nanpercentile(L[m],5)),L_p95=float(np.nanpercentile(L[m],95)),
                chroma=float(C[m].mean()),checker=checker,lit_lr=float(left-right),lit_tb=float(top-bot),colours=len(cols),
                shades=float(shades),step=float(step))
def game(C,LAB,pics):
    rows=[]
    for p in pics:
        if ('BMP ',p) not in C: continue
        fr=frames(C,'BMP ',p)[0]; st=stats(fr,LAB)
        if st: st['pic']=p; rows.append(st)
    return rows
sl=game(A,SLLAB,[r[0] for r in SLCRE]); wr=game(B,WRLAB,WRLIST)
import statistics
out={}
for name,rows in (('SL',sl),('WR',wr)):
    out[name]={k:statistics.median(r[k] for r in rows) for k in rows[0] if k!='pic'}
    print(name,len(rows),'figures (front frame, medians):')
    for k,v in out[name].items(): print(f'   {k:10} {v:8.2f}')
json.dump({"SL":sl,"WR":wr,"med":out},open("style.json","w"),default=float)
