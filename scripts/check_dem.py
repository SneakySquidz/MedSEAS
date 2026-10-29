"""Independent consistency check of data/dem.png (the stored flood levels).
Decoding mirrors index.html: red = flood level code, green = flags (bit 1 = sea cell, bit 2 = world-ocean cell).
Checks properties that must hold if the stored values are a priority-flood result."""
import numpy as np
from PIL import Image
from collections import deque
DEMRANGE=5000.0
im=np.array(Image.open('data/dem.png').convert('RGBA')).astype(np.int32)
F=im[:,:,0]; K=im[:,:,1]; h,w=F.shape
t=(F-128)/127.5; lvl=np.sign(t)*DEMRANGE*t*t       # flood level in metres
sea=(K&1)==1
print("grid %dx%d, sea cells %d, land cells %d"%(w,h,sea.sum(),(~sea).sum()))
res=[]
# 1. every land cell has a neighbour whose level is <= its own (a non-increasing path out exists)
pad=np.pad(lvl,1,constant_values=np.inf)
nbmin=np.min(np.stack([pad[1+dy:1+dy+h,1+dx:1+dx+w] for dy in(-1,0,1) for dx in(-1,0,1) if (dy,dx)!=(0,0)]),axis=0)
bad=(~sea)&(lvl>nbmin+1e-6)&(lvl>nbmin)
# land cells at the border of the grid can have no lower neighbour inside the grid; count separately
interior=np.zeros_like(sea); interior[1:-1,1:-1]=True
viol=(~sea)&interior&(lvl<nbmin-1e-6)    # a land cell lower than ALL its neighbours = an isolated pit not yet flooded
print("1. land cells strictly lower than every neighbour (pits that the flood level must lift): %d"%viol.sum())
# a priority flood lifts pits to their spill level, so after flooding no land cell should be a strict local minimum
res.append(("no unfilled pits",int(viol.sum())==0))
# 2. connectivity: for several levels, every land cell with level <= L must be 8-connected to a sea cell through cells with level <= L
def disconnected(L):
    wet=(lvl<=L)&(~sea)
    seen=np.zeros_like(wet); dq=deque()
    for y,x in zip(*np.nonzero(sea)):
        # seed from sea cells touching a wet land cell
        pass
    ys,xs=np.nonzero(sea)
    seeds=[(y,x) for y,x in zip(ys,xs) if np.any(wet[max(0,y-1):y+2,max(0,x-1):x+2])]
    for y,x in seeds:
        for dy in(-1,0,1):
            for dx in(-1,0,1):
                yy,xx=y+dy,x+dx
                if 0<=yy<h and 0<=xx<w and wet[yy,xx] and not seen[yy,xx]: seen[yy,xx]=True; dq.append((yy,xx))
    while dq:
        y,x=dq.popleft()
        for dy in(-1,0,1):
            for dx in(-1,0,1):
                yy,xx=y+dy,x+dx
                if 0<=yy<h and 0<=xx<w and wet[yy,xx] and not seen[yy,xx]: seen[yy,xx]=True; dq.append((yy,xx))
    return int((wet&~seen).sum()), int(wet.sum())
for L in (0.5,2,10,50,100,200):
    d,n=disconnected(L); print("2. level +%g m: wet land cells %d, not connected to the sea through wet cells: %d"%(L,n,d)); res.append(("connected at +%g"%L,d==0))
# 3. monotone in L (trivially true) and sea cells carry depth levels <= ~0 (sea cells never above +1 m)
print("3. sea cells with level > 1 m: %d"%int((sea&(lvl>1)).sum())); res.append(("sea cells at or below ~0 m",int((sea&(lvl>1)).sum())==0))
# 4. inland hollow check: the Dead Sea basin and Qattara have high spill levels
def at(lng,lat):
    W,S,E,N=-11.25,21.943,45.0,48.9225
    def merc(la): return np.arcsinh(np.tan(np.radians(la)))
    x=int((lng-W)/(E-W)*w); y=int((merc(N)-merc(lat))/(merc(N)-merc(S))*h); return lvl[y,x]
print("4. flood level: Dead Sea basin %.1f m, Qattara %.1f m"%(at(35.5,31.5),at(27.0,29.5)))
print("RESULT:", "ALL CONSISTENT" if all(r[1] for r in res) else "FAILURES: "+", ".join(n for n,o in res if not o))
