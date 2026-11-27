import sys,struct,os,glob,json
import numpy as np
sys.path.insert(0,'/home/user/darksun-recompiled/tools')
import sl_figures as s
def lab_arr(rgb):
    a=rgb/255.0; a=np.where(a>0.04045,((a+0.055)/1.055)**2.4,a/12.92)
    M=np.array([[0.4124,0.3576,0.1805],[0.2126,0.7152,0.0722],[0.0193,0.1192,0.9505]])
    xyz=a@M.T/np.array([0.95047,1,1.08883]); f=np.where(xyz>0.008856,np.cbrt(xyz),7.787*xyz+16/116)
    return np.stack([116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])],-1)
def region(game,path,pal,O):
    _,C=s.load(path); m=np.frombuffer(C[next(k for k in C if k[0] in('RMAP','MAP '))],dtype=np.uint8).reshape(98,128)
    tiles={}
    for (t,i),v in C.items():
        if t=='TILE':
            w,h,px=s.decode_any(v,0)
            if (w,h)==(16,16): tiles[i]=np.array([[(-1 if q is None else q) for q in r] for r in px])
    G=np.full((98*16,128*16),-1,int)
    for r in range(98):
        for c in range(128):
            t=tiles.get(m[r,c])
            if t is not None: G[r*16:r*16+16,c*16:c*16+16]=t
    ob=np.full_like(G,-1)
    e=C[next(k for k in C if k[0]=='ETAB')] if any(k[0]=='ETAB' for k in C) else b''
    n=0; sizes=[]
    for x,y,h,fl,o in sorted((struct.unpack_from('<HHBBh',e,8*k) for k in range(len(e)//8)),key=lambda t:t[1]):
        oj=O.get(('OJFF',abs(o)))
        if not oj: continue
        pic=struct.unpack_from('<H',oj,12)[0]; ax,ay=struct.unpack_from('<HH',oj,2)
        if ('BMP ',pic) not in O or ('SCMD',pic) in O: continue
        w,hh,px=s.decode_any(O[('BMP ',pic)],0); P=np.array([[(-1 if q is None else q) for q in r] for r in px])
        L,T=x-ax,y-h-ay
        if L<0 or T<0 or L+w>G.shape[1] or T+hh>G.shape[0]: continue
        sub=ob[T:T+hh,L:L+w]; sub[P>=0]=P[P>=0]; n+=1; sizes.append(w*hh)
    palarr=np.array(pal,float); LAB=lab_arr(palarr)
    used=G>=0
    if used.sum()==0: return None
    g0=G[used]; void=float((LAB[g0][:,0]<4).mean()); g=g0[LAB[g0][:,0]>=4]; Lg=LAB[g]
    # ground texture: mean |dL| to right neighbour, and checker (alternating) share
    Lmap=np.where(G>=0,LAB[np.clip(G,0,255)][...,0],np.nan)
    dl=np.abs(np.diff(Lmap,axis=1)); d2=Lmap[:,1:-1]-Lmap[:,:-2]; d3=Lmap[:,2:]-Lmap[:,1:-1]
    checker=np.nanmean(((d2*d3)<-25).astype(float)[~np.isnan(d2*d3)])
    full=np.where(ob>=0,ob,G); fu=full>=0
    return dict(game=game,region=os.path.basename(path),ground_L=float(Lg[:,0].mean()),ground_C=float(np.hypot(Lg[:,1],Lg[:,2]).mean()),
        ground_contrast=float(np.nanmean(dl)),checker=float(checker),colours=int(len(np.unique(full[fu]))),
        obj_cover=float((ob>=0).sum()/used.sum()),objects=n,obj_size=float(np.median(sizes)) if sizes else 0,tiles=len(tiles),
        void=void)
out=[]
_,AO=s.load('/tmp/playtest/inst/SEGOBJEX.GFF'); _,GP=s.load('/tmp/playtest/inst/GPLDATA.GFF')
for f in sorted(glob.glob('/tmp/playtest/inst/RGN*.GFF')):
    n=int(os.path.basename(f)[3:5],16)
    if ('PAL ',n) in GP:
        r=region('SL',f,s.vga(GP[('PAL ',n)]),AO); r and out.append(r)
_,BO=s.load('/tmp/playtest/rav/OBJEX.GFF')
for f in sorted(glob.glob('/tmp/playtest/rav/RGN*.GFF')):
    _,C=s.load(f); r=region('WR',f,s.vga(C[next(k for k in C if k[0]=='PAL ')]),BO); r and out.append(r)
json.dump(out,open('metrics.json','w'),indent=0)
import statistics
for g in ('SL','WR'):
    rs=[r for r in out if r['game']==g]
    print(g,len(rs),'regions')
    for k in ('ground_L','ground_C','ground_contrast','checker','colours','obj_cover','objects','obj_size','tiles','void'):
        v=[r[k] for r in rs]; print(f'   {k:16} median {statistics.median(v):9.3f}   range {min(v):9.3f} .. {max(v):9.3f}')
