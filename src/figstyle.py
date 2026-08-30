"""VISHWAS — the figure visual language, in one place.

Every figure in figures/ shares this palette so the set reads as one system.
The values are the established ones; they are not up for redecoration.

    surface      #fcfcfb   the paper
    ink          #0b0b0b   titles, axis labels, the numbers that matter
    ink2         #52514e   subtitles, footnotes, tick labels
    grid         #e6e5e1   gridlines and spines
    sequential   #cde2fb -> #0d366b   one quantity, low to high
    categorical  #2a78d6 (slot 1) / #eb6834 (slot 2)

All figures are 200 dpi, and the title and subtitle are FIGURE text
(fig.text), not axes titles, so they align to the page rather than to the plot
box. Footnotes carry the truth source and sample size — that convention is
what makes the numbers credible, so keep it.

NOTE: src/11_inversion.py predates this module and carries its own copy of the
palette. It is verified byte-for-byte against the shipped deck figure, so it is
deliberately left alone rather than churned; migrate it when it next changes.
"""

import textwrap

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e6e5e1"

SEQ_LOW = "#cde2fb"
SEQ_HIGH = "#0d366b"
CAT1 = "#2a78d6"
CAT2 = "#eb6834"

DPI = 200

SEQUENTIAL = LinearSegmentedColormap.from_list(
    "vishwas_seq", [SEQ_LOW, SEQ_HIGH])


def figure(width, height):
    """A figure on the project surface."""
    return plt.figure(figsize=(width, height), dpi=DPI, facecolor=SURFACE)


def axes(fig, rect):
    """Axes on the project surface, with the project's spines and grid."""
    ax = fig.add_axes(rect)
    ax.set_facecolor(SURFACE)
    ax.tick_params(colors=INK2, labelsize=13, length=4)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.set_axisbelow(True)
    return ax


def title(fig, title_text, subtitle_text, x=0.045, y=0.955,
          title_size=31, subtitle_size=17, gap=0.067):
    """Title and subtitle as figure text, left-aligned to the page."""
    fig.text(x, y, title_text, fontsize=title_size, fontweight="bold",
             color=INK, ha="left", va="top")
    if subtitle_text:
        fig.text(x, y - gap, subtitle_text, fontsize=subtitle_size, color=INK2,
                 ha="left", va="top", linespacing=1.5)


def footnote(fig, text, x=0.045, y=0.115, size=12.5, width=148):
    """Wrapped footnote. Every figure states its truth source and sample size."""
    wrapped = "\n".join("\n".join(textwrap.wrap(par, width))
                        for par in text.split("\n"))
    fig.text(x, y, wrapped, fontsize=size, color=INK2, ha="left", va="top",
             linespacing=1.6)


def save(fig, path):
    fig.savefig(path, dpi=DPI, facecolor=SURFACE)
    print("wrote {}".format(path))
