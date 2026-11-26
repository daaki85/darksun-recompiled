"""exact_frame(PNG, PAL_CHUNK): the game's 320x200 frame as palette numbers from a 640x480 DOSBox grab of
Wake of the Ravager (pixels doubled across, rows repeated 2 or 3 times: the first row of each repeat
is exact), with the distance to the nearest palette colour (0 everywhere on a clean grab)."""
import sys
import numpy as np
sys.path.insert(0,'/home/user/darksun-recompiled/tools')
import sl_figures as s
from PIL import Image
def exact_frame(png, pal_chunk):
    """The game's 320x200 frame as palette numbers, from a 640x480 DOSBox grab (pixels doubled
    across, rows repeated 2 or 3 times)."""
    g=np.array(Image.open(png).convert('RGB')).astype(int)
    rows=[0]+[y for y in range(1,480) if (g[y]!=g[y-1]).any()]
    f=g[rows][:, 0::2]
    dos=np.array([[(pal_chunk[3*i+j]&63)*4+(pal_chunk[3*i+j]&63)//16 for j in range(3)] for i in range(256)])
    d=((f[:,:,None,:]-dos[None,None,:,:])**2).sum(3)
    return d.argmin(2), d.min(2), len(rows)
