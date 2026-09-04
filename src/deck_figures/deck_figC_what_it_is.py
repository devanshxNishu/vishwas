# -*- coding: utf-8 -*-
# Slide 2, left. The concept diagram: ensemble in, three labels out.
# "23 features, none from the truth" and "calibrated bust probability" are the
# two claims this figure makes. Both are checkable against CLAUDE.md.
from deck_style import *
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

fig = plt.figure(figsize=(8.4, 3.05), dpi=220)
ax = fig.add_axes([0,0,1,1]); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
head(fig, "VISHWAS is a layer on top of the forecast, not another forecast",
     "It scores every rainfall forecast by location and lead time, Day 1 to Day 10.", y=0.965)

BY, BH = 0.215, 0.415          # band geometry
# LEFT : the ensemble you already run
lx0, lx1 = 0.048, 0.300
ax.add_patch(FancyBboxPatch((lx0,BY),lx1-lx0,BH, boxstyle="round,pad=0,rounding_size=0.012",
             fc=GREY, ec=LINE, lw=1.0, zorder=1))
rng=np.random.default_rng(4)
base=np.linspace(0,1,90)
for k in range(11):
    amp = 0.030+0.016*rng.random()
    ph  = rng.random()*6.3
    y = BY+BH*0.56 + amp*np.sin(base*7.5+ph) + 0.010*rng.standard_normal(90).cumsum()/9
    ax.plot(lx0+0.022+base*(lx1-lx0-0.044), y, color=BLUE_L, lw=1.0, alpha=0.85, zorder=2)
ax.text((lx0+lx1)/2, BY+BH-0.055, "11 ENSEMBLE MEMBERS", fontsize=8.6, color=MUTE,
        ha='center', va='top', fontweight='bold')
ax.text((lx0+lx1)/2, BY+0.045, "the forecast you already run", fontsize=9.6,
        color=INK, ha='center', va='bottom')

ax.add_patch(FancyArrowPatch((0.312,BY+BH/2),(0.372,BY+BH/2),
             arrowstyle='-|>', mutation_scale=15, color=FAINT, lw=1.5, zorder=3))

# MIDDLE : VISHWAS
mx0, mx1 = 0.384, 0.612
ax.add_patch(FancyBboxPatch((mx0,BY),mx1-mx0,BH, boxstyle="round,pad=0,rounding_size=0.014",
             fc=BLUE, ec='none', zorder=2))
ax.text((mx0+mx1)/2, BY+BH*0.66, "VISHWAS", fontsize=20, fontweight='bold',
        color='white', ha='center', va='center')
ax.text((mx0+mx1)/2, BY+BH*0.34, "reliability layer", fontsize=10.5,
        color=BLUE_XL, ha='center', va='center')
ax.text((mx0+mx1)/2, BY-0.045, "23 features, none from the truth", fontsize=9,
        color=MUTE, ha='center', va='top')

ax.add_patch(FancyArrowPatch((0.624,BY+BH/2),(0.684,BY+BH/2),
             arrowstyle='-|>', mutation_scale=15, color=FAINT, lw=1.5, zorder=3))

# RIGHT : the three labels
rx0, rw = 0.696, 0.256
pills=[("RELIABLE",GREEN,GREEN_L),("UNCERTAIN",AMBER,AMBER_L),("HIGH-RISK",RED,RED_L)]
ph_ = 0.108; gap = 0.037
for i,(lab,c,cl) in enumerate(pills):
    yy = BY+BH-ph_-i*(ph_+gap)
    ax.add_patch(FancyBboxPatch((rx0,yy),rw,ph_, boxstyle="round,pad=0,rounding_size=0.010",
                 fc=cl, ec=c, lw=1.2, zorder=2))
    ax.add_patch(FancyBboxPatch((rx0,yy),0.020,ph_, boxstyle="round,pad=0,rounding_size=0.010",
                 fc=c, ec='none', zorder=3))
    ax.text(rx0+rw/2+0.010, yy+ph_/2, lab, fontsize=11.2, fontweight='bold',
            color=c, ha='center', va='center', zorder=4)
ax.text(rx0+rw/2, BY-0.045, "calibrated bust probability", fontsize=9,
        color=MUTE, ha='center', va='top')

fig.text(0.048, 0.115, "It flags busts. It does not change the forecast.",
         fontsize=11, color=BLUE, fontweight='bold', va='top')
fig.savefig("figC_what_it_is.png", dpi=220)
noink("figC_what_it_is.png")
