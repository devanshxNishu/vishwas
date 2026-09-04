# -*- coding: utf-8 -*-
# Slide 3, lower left. 23 features in five groups; the 6 disagreement features
# are highlighted because they are the whole of the incumbent method.
# shear_500_850 has NO spread counterpart - it is derived physics, not
# disagreement. Do not move it into the blue group.
from deck_style import *
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

FW, FH = 8.4, 2.85
fig = plt.figure(figsize=(FW, FH), dpi=220)
ax = fig.add_axes([0,0,1,1]); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
head(fig, "What the model sees",
     "23 features, every one from the ensemble forecast. None from the truth.", y=0.965, ts=15)
AR = FW/FH                                     # to make visual squares

GROUPS=[("ENSEMBLE STATE",8,"mean fields",GREY,LINE,False),
        ("DISAGREEMENT",6,"members differ",BLUE,BLUE,True),
        ("DERIVED PHYSICS",4,"shear, gradient",GREY,LINE,False),
        ("VS CLIMATOLOGY",3,"anomalies",GREY,LINE,False),
        ("TIME",2,"month, lead",GREY,LINE,False)]

X0, X1, gapw = 0.048, 0.952, 0.030
sq   = (X1-X0-(len(GROUPS)-1)*gapw)/23.0
side = sq*0.78
sh   = side*AR                                  # square height in fig fraction
YT   = 0.635
x = X0
for name,n,sub,fc,ec,hi in GROUPS:
    gx0, gw = x, n*sq
    for k in range(n):
        cx = x + k*sq + (sq-side)/2
        ax.add_patch(FancyBboxPatch((cx,YT-sh),side,sh,
                     boxstyle="round,pad=0,rounding_size=0.005",
                     fc=fc, ec=ec, lw=1.3 if hi else 1.0, zorder=3))
    ax.text(gx0+gw/2, YT-sh-0.055, str(n), fontsize=16 if hi else 13.5,
            fontweight='bold', color=BLUE if hi else INK, ha='center', va='top')
    ax.text(gx0+gw/2, YT-sh-0.170, name, fontsize=8.0, fontweight='bold',
            color=BLUE if hi else MUTE, ha='center', va='top')
    ax.text(gx0+gw/2, YT-sh-0.265, sub, fontsize=7.4, color=FAINT, ha='center', va='top')
    x += gw + gapw

fig.text(0.048, 0.150,
  "Six of the twenty-three measure where the 11 members disagree with each other.",
  fontsize=10.8, color=BLUE, fontweight='bold', va='top')
fig.text(0.048, 0.078,
  "That disagreement is the whole of the method forecasters use today. Here it is one input among twenty-three.",
  fontsize=9.4, color=MUTE, va='top')
fig.savefig("figD_features.png", dpi=220)
noink("figD_features.png")
