import sys,struct
sys.path.insert(0,'../fig')
from region import draw
from common import *
from PIL import Image, ImageDraw
_,P=s.load('/tmp/playtest/swap1_OBJEX.GFF')
def place(im,fr,cx,base):
    h,w=fr.shape
    for y in range(h):
        for x in range(w):
            q=fr[y,x]
            if q>=0:
                X,Y=cx-w//2+x,base-h+y
                if 0<=X<im.width and 0<=Y<im.height: im.putpixel((X,Y),WRPAL[q])
def scene(C):
    im=draw('WR',0x032,(1008,1368,320,200))
    party=[struct.unpack_from('<H',P[('OJFF',o)],12)[0] for o in (300,305,308,313,306)]
    row1=[(P,party[0],40),(P,party[1],70),(P,party[2],102),(C,2843,150),(C,2850,205),(C,693,262)]
    row2=[(P,party[3],40),(P,party[4],72),(C,1753,130),(C,2555,200)]
    for base,row in ((86,row1),(176,row2)):
        for src,pic,cx in row: place(im,frames(src,'BMP ',pic)[0],cx,base)
    return im
_,V1=s.load('OBJEX_restyled_v1.GFF'); _,V2=s.load('OBJEX_restyled.GFF')
a=scene(V1); b=scene(V2)
b.resize((640,400),Image.NEAREST).save('/tmp/playtest/art-review/together-v2.png')
crop=(20,0,300,180)
za=a.crop(crop).resize(((crop[2]-crop[0])*3,(crop[3]-crop[1])*3),Image.NEAREST); zb=b.crop(crop).resize(za.size,Image.NEAREST)
z=Image.new('RGB',(za.width*2+12,za.height+24),(20,20,20)); d=ImageDraw.Draw(z)
z.paste(za,(0,24)); z.paste(zb,(za.width+12,24)); d.text((4,6),'v1 (first restyle)',fill=(255,255,0)); d.text((za.width+16,6),'v2 (tuned to the party)',fill=(255,255,0))
z.save('/tmp/playtest/art-review/together-v2-zoom.png'); print(z.size)
