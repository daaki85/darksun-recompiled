import sys,struct
sys.path.insert(0,'../fig')
from region import draw
from common import *
from PIL import Image
_,C=s.load('/tmp/playtest/restyle45_OBJEX.GFF')
def place(im,fr,cx,base):
    h,w=fr.shape
    for y,x in zip(*np.where(fr>=0)):
        X,Y=cx-w//2+int(x),base-h+int(y)
        if 0<=X<im.width and 0<=Y<im.height: im.putpixel((X,Y),WRPAL[fr[y,x]])
im=draw('WR',0x032,(1008,1368,320,200))
party=[struct.unpack_from('<H',C[('OJFF',o)],12)[0] for o in (300,305,308,313,306)]
rows=[(62,party[:3]+[2843,2852,2884]),(128,party[3:]+[693,1753,2850,2889]),(196,[2556,2554,2394,1757,2860,2537,2570])]
for base,pics in rows:
    frs=[frames(C,'BMP ',p)[0] for p in pics]; gap=(320-sum(f.shape[1] for f in frs))/(len(frs)+1); x=gap
    for f in frs: place(im,f,int(x+f.shape[1]/2),base); x+=f.shape[1]+gap
im.resize((960,600),Image.NEAREST).save('/tmp/playtest/art-review/together-45.png'); print('ok')
