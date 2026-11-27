from common import *
from PIL import Image, ImageDraw
_,R=s.load('OBJEX_restyled.GFF')
table,_=s.colour_table(SLPAL,s.wr_palettes('/tmp/playtest/rav'))
CASES=[(2843,'yuan-ti serpent folk',2128,'SL fire eel'),(2850,'verini (ape-lizard)',2153,'SL strine'),
       (693,'magma golem',2246,'SL animated statue'),(1753,'skeleton',686,'SL skeleton warrior'),
       (2555,'umber hulk',2426,'SL rampager')]
def strip(frs,pal,bg=(48,48,48)):
    W=sum(f.shape[1]+3 for f in frs); H=max(f.shape[0] for f in frs)
    im=Image.new('RGB',(W,H),bg); x=0
    for f in frs:
        for y in range(f.shape[0]):
            for xx in range(f.shape[1]):
                q=f[y,xx]
                if q>=0: im.putpixel((x+xx,H-f.shape[0]+y),pal[q])   # bottom-aligned: same ground line
        x+=f.shape[1]+3
    return im
for pic,name,slp,slname in CASES:
    rows=[('WR '+str(pic)+' walking',strip(frames(B,'BMP ',pic),WRPAL)),('restyled walking',strip(frames(R,'BMP ',pic),WRPAL))]
    if ('CBMP',pic) in B:
        rows+= [('WR combat',strip(frames(B,'CBMP',pic),WRPAL)),('restyled combat',strip(frames(R,'CBMP',pic),WRPAL))]
    slfr=[np.vectorize(lambda q: table[q] if q>=0 else -1)(f) for f in frames(A,'BMP ',slp)]
    rows.append((f'{slname} {slp} (SL style, same scale, WR colours)',strip(slfr,WRPAL)))
    W=max(r[1].width for r in rows)+4; H=sum(r[1].height+14 for r in rows)+18
    sh=Image.new('RGB',(W,H),(30,30,30)); d=ImageDraw.Draw(sh); d.text((2,2),f'{name}: WR {pic}',fill=(255,255,0)); y=18
    for lbl,im in rows:
        d.text((2,y),lbl,fill=(200,200,200)); sh.paste(im,(2,y+12)); y+=im.height+14
    sh=sh.resize((sh.width*2,sh.height*2),Image.NEAREST)
    out=f'/tmp/playtest/art-review/restyle_{pic}.png'; sh.save(out); print(out,sh.size)
