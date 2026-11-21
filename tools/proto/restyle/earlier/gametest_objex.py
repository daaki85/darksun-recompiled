# test only: the ambush's Draxans (objects 202, 206, 207) drawn as restyled creatures
from common import *
import struct
_,R=s.load('/tmp/playtest/restyle45_OBJEX.GFF')
import os
MAP=eval(os.environ.get('RSMAP','{200:414,204:434}'))    # Draxan object -> the object whose picture and anchor it borrows
ch={}
for d,src in MAP.items():
    r=bytearray(R[('OJFF',d)]); o=R[('OJFF',src)]
    r[2:6]=o[2:6]; r[12:14]=o[12:14]; ch[('OJFF',d)]=bytes(r)
    print(d,'->',struct.unpack_from('<H',o,12)[0])
s.write_ranged('/tmp/playtest/restyle45_OBJEX.GFF',ch,'/tmp/playtest/ravrs/OBJEX.GFF')
_,T2=s.load('/tmp/playtest/ravrs/OBJEX.GFF')
assert all(T2[k]==v for k,v in ch.items()); print('ok')
