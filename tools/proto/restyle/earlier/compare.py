from common import *
T=json.load(open('party_target.json'))
_,V1=s.load('OBJEX_restyled_v1.GFF'); _,V2=s.load('OBJEX_restyled.GFF')
def pooled(C,pic):
    L=[];Cc=[];ed=[];lr=[];tb=[]
    for t in ('BMP ','CBMP'):
        if (t,pic) not in C: continue
        for fr in frames(C,t,pic):
            m=fr>=0
            if m.sum()<20: continue
            lab=WRLAB[np.clip(fr,0,255)]; L+=list(lab[...,0][m]); Cc+=list(np.hypot(lab[...,1],lab[...,2])[m])
            pad=np.pad(m,1); e=m&~(pad[:-2,1:-1]&pad[2:,1:-1]&pad[1:-1,:-2]&pad[1:-1,2:]); ed.append((lab[...,0][e]<25).mean())
            ys,xs=np.where(m); cx=(xs.min()+xs.max())/2; cy=(ys.min()+ys.max())/2; Lm=np.where(m,lab[...,0],np.nan)
            X,Y=np.meshgrid(np.arange(fr.shape[1]),np.arange(fr.shape[0]))
            lr.append(np.nanmean(np.where(X<cx,Lm,np.nan))-np.nanmean(np.where(X>cx,Lm,np.nan))); tb.append(np.nanmean(np.where(Y<cy,Lm,np.nan))-np.nanmean(np.where(Y>cy,Lm,np.nan)))
    L=np.array(L); Cc=np.array(Cc)
    return [L.mean(),L.std(),Cc.mean(),np.percentile(Cc,90),np.mean(ed)*100,np.nanmedian(lr),np.nanmedian(tb)]
hdr='L mean, L sd, chroma mean, chroma p90, dark edges %, lit L-R, lit T-B'
print('party target :',' '.join(f'{v:6.1f}' for v in [T['L_mean'],T['L_sd'],T['C_mean'],T['C_p90'],T['edge_dark']*100,T['lit_lr'],T['lit_tb']]),' (',hdr,')')
for p in (2843,2850,693,1753,2555):
    for nm,C in (('WR',B),('v1',V1),('v2',V2)):
        print(f'{p:5} {nm} :',' '.join(f'{v:6.1f}' for v in pooled(C,p)))
