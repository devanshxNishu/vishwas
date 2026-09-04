# -*- coding: utf-8 -*-
# Slide 4, right. REPLACES fig4_inversion and figB_tie, which used to sit on
# this slide as two separate graphics and collided with the risk heading.
# NOTE: this figure does NOT carry fig4's old footnote about "five wet-point
# definitions". The +0.13 to +0.16 range spans TWO variants (all bins, drop the
# driest bin) - see CLAUDE.md P18. Five is right on slide 6, wrong here.
from deck_style import *
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

FW,FH = 6.9, 5.55
fig = plt.figure(figsize=(FW,FH), dpi=220)
ax = fig.add_axes([0,0,1,1]); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
AR = FW/FH

fig.text(0.058, 0.972, "What the crude comparison hides", fontsize=15.5,
         fontweight='bold', color=INK, va='top')
fig.text(0.058, 0.925, "Two ways the incumbent method looks better than it is.",
         fontsize=10.4, color=MUTE, va='top')

# PART 1 : the inversion
bx = fig.add_axes([0.135, 0.575, 0.60, 0.270]); bx.set_facecolor(SURF)
vals=[0.023,0.163]; labs=["Compared\ncrudely","Compared\nfairly"]
bars=bx.bar([0,1],vals,width=0.50,color=[BLUE_L,BLUE],zorder=3)
for b in bars: b.set_linewidth(0)
bx.errorbar(1,0.163,yerr=[[0.163-0.108],[0.193-0.163]],fmt='none',
            ecolor=INK,elinewidth=1.5,capsize=6,capthick=1.5,zorder=5)
bx.text(0,0.023+0.011,"+0.023",ha='center',va='bottom',fontsize=13,color=MUTE,fontweight='bold')
bx.text(1,0.200,"+0.163",ha='center',va='bottom',fontsize=19,color=BLUE,fontweight='bold')
bx.set_xticks([0,1]); bx.set_xticklabels(labs,fontsize=10.2,color=INK,linespacing=1.35)
bx.set_yticks([]); bx.set_ylim(0,0.250); bx.set_xlim(-0.62,1.62)
for s in ("top","right","left"): bx.spines[s].set_visible(False)
bx.spines['bottom'].set_color(LINE); bx.spines['bottom'].set_linewidth(1.1)
bx.tick_params(axis='x',length=0,pad=7)
bx.annotate("", xy=(0.735,0.062), xytext=(0.415,0.062),
            arrowprops=dict(arrowstyle="-|>",color=AMBER,lw=1.6), zorder=6)
bx.text(0.575,0.082,"7×",fontsize=13,color=AMBER,fontweight='bold',
        ha='center',va='bottom')
fig.text(0.058, 0.470, "VISHWAS's margin over ensemble spread (ROC-AUC). Compared fairly it is seven times larger.",
         fontsize=9.2, color=MUTE, va='top')
fig.text(0.058, 0.433, "Pooling lets ensemble spread track how hard it is raining, and hands it skill it never earned.",
         fontsize=9.2, color=MUTE, va='top')

ax.add_line(Line2D([0.058,0.942],[0.405,0.405],color=LINE,lw=1.1,zorder=1))

# PART 2 : the tie
TOT,TIE=651040,189758; frac=TIE/TOT
ax.text(0.058, 0.368, "189,758", fontsize=30, fontweight='bold', color=BLUE, va='top')
ax.text(0.360, 0.338, "forecasts where ensemble", fontsize=10.6, color=INK, va='top')
ax.text(0.360, 0.281, "spread is exactly 0.00 mm", fontsize=10.6, color=INK, va='top')
y0,h = 0.165, 0.055
ax.add_patch(FancyBboxPatch((0.058,y0),0.884,h, boxstyle="round,pad=0,rounding_size=0.006",
             fc="#E9EDF1", ec='none', zorder=1))
ax.add_patch(FancyBboxPatch((0.058,y0),0.884*frac,h, boxstyle="round,pad=0,rounding_size=0.006",
             fc=BLUE, ec='none', zorder=2))
ax.text(0.058+0.884*frac/2, y0+h/2, "29%", ha='center', va='center', color='white',
        fontsize=11, fontweight='bold', zorder=4)
ax.text(0.058+0.884*frac+0.016, y0+h/2, "of the 651,040 forecast test set",
        ha='left', va='center', color=MUTE, fontsize=9.2, zorder=4)
ax.text(0.058, 0.124, "One tie the incumbent cannot rank.", fontsize=11.2,
        color=AMBER, fontweight='bold', va='top')
ax.text(0.058, 0.064, "VISHWAS ranks inside it.", fontsize=11.2,
        color=BLUE, fontweight='bold', va='top')
fig.savefig("figE_slide4.png", dpi=220); noink("figE_slide4.png")
