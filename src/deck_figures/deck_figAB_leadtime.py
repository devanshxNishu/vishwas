# -*- coding: utf-8 -*-
# Slide 5, right: figA. The five accuracy figures are the Ministry's own, quoted
# from Lok Sabha Q. 2953 - do not round, re-derive or interpolate them.
# figB (the tie block) is NO LONGER ON THE DECK; it was folded into
# deck_figE_slide4.py. It is kept here only so the old asset can be reproduced.
from deck_style import *
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# FIG A : IMD warning accuracy falls with lead time
FW,FH = 8.4, 3.10
fig = plt.figure(figsize=(FW,FH), dpi=220)
head(fig, "IMD's warning accuracy falls with lead time",
     "Correct heavy-rainfall warnings, Day 1 to Day 5.\nThis is exactly the window VISHWAS scores.", y=0.965)
ax = fig.add_axes([0.048, 0.300, 0.735, 0.395]); ax.set_ylim(0,100)
days=["Day 1","Day 2","Day 3","Day 4","Day 5"]; acc=[85,73,67,63,58]
cols=[BLUE]*4+[AMBER]
bars=ax.bar(days,acc,width=0.56,color=cols,zorder=3)
for i,(b,v) in enumerate(zip(bars,acc)):
    b.set_linewidth(0); strong = i in (0,4)
    ax.text(b.get_x()+b.get_width()/2, v+3.5, f"{v}%", ha='center', va='bottom',
            fontsize=19 if strong else 13.5, fontweight='bold' if strong else 'normal',
            color=(INK if i==0 else AMBER) if strong else MUTE, zorder=4)
ax.set_yticks([]); ax.set_ylim(0,104)
ax.tick_params(axis='x', labelsize=12, length=0, pad=7)
for s in ("top","right","left"): ax.spines[s].set_visible(False)
ax.spines['bottom'].set_color(LINE); ax.spines['bottom'].set_linewidth(1.1)
ax.add_patch(FancyArrowPatch((4.40,85),(4.40,60), arrowstyle='-|>', mutation_scale=13,
             color=AMBER, lw=1.6, clip_on=False, zorder=5))
ax.text(4.56, 72, "27 points lost\nin four days", fontsize=10.6, color=AMBER,
        va='center', ha='left', fontweight='bold', clip_on=False, linespacing=1.35)
source(fig, "Ministry of Earth Sciences, Lok Sabha Q. 2953, 17 December 2025.\nThe Ministry reports these five figures directly.", y=0.140)
fig.savefig("figA_imd_leadtime.png", dpi=220); noink("figA_imd_leadtime.png")

# FIG B : the tie the incumbent cannot rank - RETIRED, folded into figE
TOT, TIE = 651040, 189758; frac=TIE/TOT
FW,FH = 8.4, 1.90
fig = plt.figure(figsize=(FW,FH), dpi=220)
ax = fig.add_axes([0,0,1,1]); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
ax.text(0.030, 0.965, "189,758", fontsize=34, fontweight='bold', color=BLUE, va='top')
ax.text(0.310, 0.905, "forecasts where ensemble spread", fontsize=11.4, color=INK, va='top')
ax.text(0.310, 0.720, "is exactly 0.00 mm", fontsize=11.4, color=INK, va='top')
BX0, BW = 0.030, 0.700
y0, h = 0.360, 0.185
ax.add_patch(FancyBboxPatch((BX0,y0),BW,h, boxstyle="round,pad=0,rounding_size=0.008",
             fc="#E9EDF1", ec='none', zorder=1))
ax.add_patch(FancyBboxPatch((BX0,y0),BW*frac,h, boxstyle="round,pad=0,rounding_size=0.008",
             fc=BLUE, ec='none', zorder=2))
ax.text(BX0+BW*frac/2, y0+h/2, "29%", ha='center', va='center', color='white',
        fontsize=12.5, fontweight='bold', zorder=4)
ax.text(BX0+BW+0.016, y0+h/2, "of the 651,040\nforecast test set", ha='left',
        va='center', color=MUTE, fontsize=9.2, zorder=4, linespacing=1.3)
ax.text(0.030, 0.245, "One tie the incumbent cannot rank.", fontsize=11.8,
        color=AMBER, fontweight='bold', va='top')
ax.text(0.470, 0.245, "VISHWAS ranks inside it.", fontsize=11.8,
        color=BLUE, fontweight='bold', va='top')
fig.savefig("figB_tie.png", dpi=220); noink("figB_tie.png")
