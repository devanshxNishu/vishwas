# -*- coding: utf-8 -*-
# Shared design system for the SIH deck figures (slides 2-5).
# Every figure on the deck is produced by a script in this folder. Numbers live
# in the scripts, never in a person's retyping of them.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
BLUE="#00549E"; BLUE_L="#7FB2DC"; BLUE_XL="#DCEAF7"
AMBER="#A96200"; AMBER_L="#F2D9AF"
GREEN="#1B6E33"; GREEN_L="#CFE6D6"
RED="#B31E1E";   RED_L="#F3CFCC"
INK="#16202B"; MUTE="#6B7785"; FAINT="#9AA5B1"
LINE="#DCE3EA"; SURF="#FCFCFB"; GREY="#EEF1F4"
plt.rcParams.update({
 'font.family':["DejaVu Sans"],'text.color':INK,
 'axes.edgecolor':LINE,'axes.labelcolor':MUTE,
 'xtick.color':MUTE,'ytick.color':MUTE,
 'figure.facecolor':SURF,'axes.facecolor':SURF,'savefig.facecolor':SURF})

def head(fig, title, sub=None, x=0.048, y=0.955, ts=15, ss=10.6):
    fig.text(x, y, title, fontsize=ts, fontweight='bold', color=INK, va='top')
    if sub: fig.text(x, y-0.098, sub, fontsize=ss, color=MUTE, va='top', linespacing=1.35)

def source(fig, txt, x=0.048, y=0.072):
    fig.text(x, y, txt, fontsize=8.4, color=FAINT, va='top', linespacing=1.4)

def noink(path):
    """assert nothing touches the canvas edges"""
    import numpy as np
    from PIL import Image
    a=np.array(Image.open(path).convert('RGB')); bg=a[2,2]
    d=lambda blk:(np.abs(blk.astype(int)-bg.astype(int)).sum(2)>18).sum()
    e={'top':d(a[:4,:,:]),'bottom':d(a[-4:,:,:]),'left':d(a[:,:4,:]),'right':d(a[:,-4:,:])}
    bad={k:v for k,v in e.items() if v}
    print(("  OVERFLOW "+str(bad)) if bad else "  edges clean", Image.open(path).size)
