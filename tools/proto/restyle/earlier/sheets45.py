import sys
from common import *
from restyle import ALL45
from PIL import Image, ImageDraw
SRC=sys.argv[1] if len(sys.argv)>1 else '/tmp/playtest/restyle45_OBJEX.GFF'; LIST=[int(a) for a in sys.argv[3:]] or ALL45; OUTP=sys.argv[2] if len(sys.argv)>2 else '/tmp/playtest/art-review/restyle45'
_,R=s.load(SRC)
P=json.load(open('/tmp/playtest/people-review/proposals.json'))
def img(f,sc=2):
    im=Image.new('RGB',(f.shape[1],f.shape[0]),(48,48,48))
    for y,x in zip(*np.where(f>=0)): im.putpixel((int(x),int(y)),WRPAL[f[y,x]])
    return im.resize((im.width*sc,im.height*sc),Image.NEAREST)
def cell(pic):
    wb=frames(B,'BMP ',pic); rb=frames(R,'BMP ',pic); k=len(wb)//2
    pairs=[('front',wb[0],rb[0]),(f'frame {k}',wb[k],rb[k])]
    if ('CBMP',pic) in B: pairs.append(('combat',frames(B,'CBMP',pic)[0],frames(R,'CBMP',pic)[0]))
    ims=[(l,img(a),img(b)) for l,a,b in pairs]
    H=max(max(a.height,b.height) for _,a,b in ims)+30; W=sum(a.width+b.width+14 for _,a,b in ims)+4
    c=Image.new('RGB',(max(W,300),H),(28,28,28)); d=ImageDraw.Draw(c)
    d.text((3,2),f"{pic}: {P[str(pic)]['wr_what'][:44]}",fill=(255,255,0)); x=3
    for l,a,b in ims:
        d.text((x,14),l+' WR|new',fill=(170,170,170))
        c.paste(a,(x,H-a.height)); c.paste(b,(x+a.width+4,H-b.height)); x+=a.width+b.width+14
    return c
cells=[cell(p) for p in LIST]
for n in range(0,len(cells),12):
    grp=cells[n:n+12]; cols=3; rows=[grp[i:i+cols] for i in range(0,len(grp),cols)]
    W=max(sum(c.width+6 for c in r) for r in rows); H=sum(max(c.height for c in r)+6 for r in rows)
    sh=Image.new('RGB',(W,H),(15,15,15)); y=0
    for r in rows:
        x=0
        for c in r: sh.paste(c,(x,y)); x+=c.width+6
        y+=max(c.height for c in r)+6
    out=f'{OUTP}_{n//12+1}.png'; sh.save(out); print(out,sh.size)
