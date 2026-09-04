# -*- coding: utf-8 -*-
# Slide 2, right. THE WORD "variance" IS LOAD-BEARING AND MUST NOT BE DROPPED:
# the claim is the share of the VARIANCE in forecast error, not "forecast error".
# Five wet-point definitions is CORRECT HERE (CLAUDE.md P18): the Phase 1
# variance range does span five. Do not "fix" it to two - that is fig4's number.
from deck_style import *
import matplotlib.pyplot as plt

FW,FH = 6.9, 4.21
fig = plt.figure(figsize=(FW,FH), dpi=220)
head(fig, "Ensemble spread explains far less than it appears to",
     "Share of the variance in forecast error that ensemble spread explains.", y=0.968, ts=14.2, ss=10.2)
ax = fig.add_axes([0.115, 0.285, 0.845, 0.445])
vals=[43.9,0.90]
bars=ax.bar([0,1],vals,width=0.46,color=[BLUE_L,BLUE],zorder=3)
for b in bars: b.set_linewidth(0)
ax.text(0,45.6,"43.9%",ha='center',va='bottom',fontsize=21,color=MUTE,fontweight='bold')
ax.text(1,2.2,"0.90%",ha='center',va='bottom',fontsize=20,color=BLUE,fontweight='bold')
ax.text(1,14.6,"effectively nothing",ha='center',va='bottom',fontsize=10.6,
        color=AMBER,fontweight='bold')
ax.set_xticks([0,1])
ax.set_xticklabels(["Compared across all of India\n(what it looks like)",
                    "Compared within the same\nrainfall regime (what it is)"],
                   fontsize=10.2,color=INK,linespacing=1.4)
ax.set_yticks([]); ax.set_ylim(0,56); ax.set_xlim(-0.62,1.62)
for s in ("top","right","left"): ax.spines[s].set_visible(False)
ax.spines['bottom'].set_color(LINE); ax.spines['bottom'].set_linewidth(1.1)
ax.tick_params(axis='x',length=0,pad=8)
source(fig, "IMD gauge-observed rainfall. 12 forecasts, four seasons, 2012 / 2015 / 2018.\n"
            "The within-regime figure is the most generous of five wet-point definitions; the range is 0.17% to 0.90%.",
       y=0.100)
fig.savefig("figF_collapse.png", dpi=220); noink("figF_collapse.png")
