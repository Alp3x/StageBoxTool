"""
Stage Box & Audio Patch Manager  (Multi-Band Edition)
------------------------------------------------------
Add as many BANDS as you want for the day. Each band gets its own
complete patch list:
  52 Input channels  |  24 Output channels
  Stage boxes: default 4 (A, B, C, D) - click "+ Add Stage Box" for more.
    - Each stage box has 12 sockets:
        Sockets  1-8  : fixed INPUTS
        Sockets  9-12 : switchable INPUT or OUTPUT (toggle in Stage Boxes tab)

All bands are visible in one window as tabs along the top.
A global "All Labels Overview" tab shows labels for all bands.
SAVE / LOAD / PRINT REPORT work across the whole show.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import string
import sys

# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────
NUM_INPUTS        = 52
NUM_OUTPUTS       = 24
NUM_SOCKETS       = 12
FIXED_IN_COUNT    = 8            
FLEX_START        = 9            
DEFAULT_BOX_COUNT = 4             
ALPHABET          = string.ascii_uppercase   

OUTPUT_TYPES = ["---", "Aux", "Auto-Tune IN", "IEM", "Record", "Other"]

# ─────────────────────────────────────────────
#  Theme  (Modern Dark Mode - Catppuccin Macchiato)
# ─────────────────────────────────────────────
BG        = "#1e1e2e"
BG2       = "#313244"
BG3       = "#45475a"
BORDER    = "#585b70"

TEXT      = "#cdd6f4"
TEXT_DIM  = "#a6adc8"
DARK_TXT  = "#11111b"

ACCENT    = "#89b4fa"  # Blue
ACCENT2   = "#f5c2e7"  # Pink

GREEN     = "#a6e3a1"
YELLOW    = "#f9e2af"
RED       = "#f38ba8"
PURPLE    = "#cba6f7"
OUT_CLR   = "#fab387"  # Peach

FONT_FAMILY = "Segoe UI" # Fallback is usually Helvetica/Arial

FT   = (FONT_FAMILY, 10)
FTS  = (FONT_FAMILY, 9)
FTX  = (FONT_FAMILY, 8)
FTB  = (FONT_FAMILY, 10, "bold")
FTH  = (FONT_FAMILY, 13, "bold")
FTTL = (FONT_FAMILY, 18, "bold")

BOX_COLORS = [
    "#89b4fa", "#a6e3a1", "#f9e2af", "#fab387", "#f38ba8", 
    "#cba6f7", "#94e2d5", "#f5c2e7", "#b4befe", "#74c7ec",
]


# ─────────────────────────────────────────────
#  Data Model
# ─────────────────────────────────────────────
def _default_box(name):
    return {
        "name":            name,
        "socket_mode":     ["IN"] * NUM_SOCKETS,
        "socket_assigned": {s: False for s in range(1, NUM_SOCKETS + 1)},
    }


class BandData:
    def __init__(self, band_name="Band 1", num_boxes=DEFAULT_BOX_COUNT):
        self.band_name = band_name
        self.box_order = []     
        self.boxes     = {}
        for _ in range(num_boxes):
            self._add_box_internal()

        self.inputs  = [{"name": "", "box": "---", "socket": 0, "note": "", "location": ""}
                         for _ in range(NUM_INPUTS)]
        self.outputs = [{"name": "", "type": "---", "box": "---", "socket": 0, "note": "", "location": ""}
                        for _ in range(NUM_OUTPUTS)]

    def _add_box_internal(self):
        letter = ALPHABET[len(self.box_order)]
        self.box_order.append(letter)
        self.boxes[letter] = _default_box(letter)
        return letter

    def add_box(self):
        if len(self.box_order) >= len(ALPHABET):
            return None
        return self._add_box_internal()

    def box_choices(self):
        return ["---"] + self.box_order

    def box_color(self, letter):
        if letter not in self.box_order:
            return TEXT_DIM
        return BOX_COLORS[self.box_order.index(letter) % len(BOX_COLORS)]

    def get_socket_mode(self, box_name, socket_num):
        if box_name not in self.boxes:
            return "IN"
        return self.boxes[box_name]["socket_mode"][socket_num - 1]

    def set_socket_mode(self, box_name, socket_num, mode):
        if box_name in self.boxes and socket_num >= FLEX_START:
            self.boxes[box_name]["socket_mode"][socket_num - 1] = mode

    def is_socket_assigned(self, box_name, socket_num):
        if box_name not in self.boxes:
            return False
        return self.boxes[box_name]["socket_assigned"].get(socket_num, False)

    def set_socket_assigned(self, box_name, socket_num, value: bool):
        if box_name in self.boxes and socket_num >= 1:
            self.boxes[box_name]["socket_assigned"][socket_num] = value

    def rebuild_assigned_from_data(self):
        for bd in self.boxes.values():
            bd["socket_assigned"] = {s: False for s in range(1, NUM_SOCKETS + 1)}
        for ch in self.inputs:
            if ch["box"] != "---" and ch["socket"] > 0 and ch["box"] in self.boxes:
                self.set_socket_assigned(ch["box"], ch["socket"], True)
        for ch in self.outputs:
            if ch["box"] != "---" and ch["socket"] > 0 and ch["box"] in self.boxes:
                self.set_socket_assigned(ch["box"], ch["socket"], True)

    def to_dict(self):
        return {
            "band_name": self.band_name,
            "box_order": self.box_order,
            "boxes":     self.boxes,
            "inputs":    self.inputs,
            "outputs":   self.outputs,
        }

    @classmethod
    def from_dict(cls, d):
        band = cls(band_name=d.get("band_name", "Band"), num_boxes=0)
        box_order = d.get("box_order") or list(ALPHABET[:DEFAULT_BOX_COUNT])
        raw_boxes = d.get("boxes", {})
        band.box_order = []
        band.boxes = {}
        for letter in box_order:
            raw = raw_boxes.get(letter) or _default_box(letter)
            sm = raw.get("socket_mode", ["IN"] * NUM_SOCKETS)
            if len(sm) < NUM_SOCKETS:
                sm += ["IN"] * (NUM_SOCKETS - len(sm))
            for i in range(FIXED_IN_COUNT):
                sm[i] = "IN"
            raw["socket_mode"] = sm
            raw.setdefault("socket_assigned", {s: False for s in range(1, NUM_SOCKETS + 1)})
            raw.setdefault("name", letter)
            band.box_order.append(letter)
            band.boxes[letter] = raw

        raw_inputs  = d.get("inputs",  band.inputs)
        raw_outputs = d.get("outputs", band.outputs)
        for ch in raw_inputs:
            ch.setdefault("location", "")
        for ch in raw_outputs:
            ch.setdefault("location", "")
        band.inputs  = raw_inputs
        band.outputs = raw_outputs
        band.rebuild_assigned_from_data()
        return band


class ShowData:
    def __init__(self):
        self.show_name = "Untitled Show"
        self.bands = [BandData(band_name="Band 1")]

    def add_band(self, name=None):
        n = len(self.bands) + 1
        band = BandData(band_name=name or f"Band {n}")
        self.bands.append(band)
        return band

    def remove_band(self, index):
        if len(self.bands) > 1 and 0 <= index < len(self.bands):
            del self.bands[index]

    def to_dict(self):
        return {"show_name": self.show_name, "bands": [b.to_dict() for b in self.bands]}

    def from_dict(self, d):
        self.show_name = d.get("show_name", "Untitled Show")
        raw_bands = d.get("bands")
        if raw_bands:
            self.bands = [BandData.from_dict(b) for b in raw_bands]
        else:
            self.bands = [BandData(band_name="Band 1")]


# ─────────────────────────────────────────────
#  Shared scrollable widgets (Seamless Scroll)
# ─────────────────────────────────────────────
def attach_mouse_scroll(container, canvas):
    """
    Binds the mouse scroll wheel robustly across Mac, Windows, and Linux.
    Using bind_all on <Enter> guarantees the scroll works even if hovering over child items.
    """
    def _on_mousewheel(event):
        # Linux Check
        if getattr(event, 'num', 0) == 4:
            canvas.yview_scroll(-1, "units")
            return
        elif getattr(event, 'num', 0) == 5:
            canvas.yview_scroll(1, "units")
            return
            
        # Mac / Windows Check
        delta = getattr(event, 'delta', 0)
        if delta != 0:
            if sys.platform == 'darwin':
                canvas.yview_scroll(int(-1 * delta), "units") # Mac is pure delta
            else:
                canvas.yview_scroll(int(-1 * (delta / 120)), "units") # Windows standardizes to 120

    def _bind_all(e):
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_mousewheel)
        canvas.bind_all("<Button-5>", _on_mousewheel)

    def _unbind_all(e):
        canvas.unbind_all("<MouseWheel>")
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")

    container.bind("<Enter>", _bind_all)
    container.bind("<Leave>", _unbind_all)


def make_scrollable(parent, horizontal=False):
    outer  = tk.Frame(parent, bg=BG)
    outer.pack(fill="both", expand=True)
    canvas = tk.Canvas(outer, bg=BG, bd=0, highlightthickness=0)
    vs     = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vs.set)
    if horizontal:
        hs = ttk.Scrollbar(outer, orient="horizontal", command=canvas.xview)
        canvas.configure(xscrollcommand=hs.set)
        hs.pack(side="bottom", fill="x")
    vs.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg=BG)
    wid   = canvas.create_window((0, 0), window=inner, anchor="nw")
    
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(wid, width=e.width))

    attach_mouse_scroll(outer, canvas)
    return outer, canvas, inner


def make_scrollframe(parent):
    canvas = tk.Canvas(parent, bg=BG, bd=0, highlightthickness=0)
    vs     = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vs.set)
    vs.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner  = tk.Frame(canvas, bg=BG)
    wid    = canvas.create_window((0, 0), window=inner, anchor="nw")
    
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(wid, width=e.width))
    
    attach_mouse_scroll(parent, canvas)
    return inner, canvas

# ─────────────────────────────────────────────
#  Report builder 
# ─────────────────────────────────────────────
def build_band_report_lines(band, width=88):
    lines = [f"BAND: {band.band_name}", "=" * width, ""]
    lines += ["STAGE BOX SOCKET CONFIG", "-" * width]
    for bn in band.box_order:
        bd   = band.boxes[bn]
        line = f"  {bd['name']:10s} ({bn}):  "
        for si in range(NUM_SOCKETS):
            mode = bd["socket_mode"][si]
            line += f"S{si+1:02d}:{mode}  "
        lines.append(line)

    lines += ["", "INPUTS", "-" * width,
              f"{'CH':<5} {'NAME':<24} {'BOX':<8} {'SOCKET':<7} {'DIR':<5} {'LOCATION':<16} {'NOTE'}"]
    for i, ch in enumerate(band.inputs):
        sstr = f"S{ch['socket']:02d}" if ch["socket"] > 0 else "-"
        mstr = band.get_socket_mode(ch["box"], ch["socket"]) \
               if ch["box"] != "---" and ch["socket"] > 0 else ""
        loc = ch.get("location", "")
        lines.append(
            f"{i+1:<5} {ch['name']:<24} {ch['box']:<8} {sstr:<7} {mstr:<5} {loc:<16} {ch['note']}")

    lines += ["", "OUTPUTS", "-" * width,
              f"{'OUT':<5} {'NAME':<24} {'TYPE':<14} {'BOX':<8} {'SOCKET':<7} {'LOCATION':<16} {'NOTE'}"]
    for i, out in enumerate(band.outputs):
        sstr = f"S{out['socket']:02d}" if out["socket"] > 0 else "-"
        loc  = out.get("location", "")
        lines.append(
            f"{i+1:<5} {out['name']:<24} {out['type']:<14} {out['box']:<8} {sstr:<7} {loc:<16} {out['note']}")

    return lines


# ─────────────────────────────────────────────
#  AllLabelsPanel - NEW GLOBAL VIEW
# ─────────────────────────────────────────────
class AllLabelsPanel(tk.Frame):
    def __init__(self, master, app, show: ShowData):
        super().__init__(master, bg=BG)
        self.app = app
        self.show = show
        self._build()

    def _build(self):
        bar = tk.Frame(self, bg=BG2, height=45)
        bar.pack(fill="x")
        tk.Label(bar, text="  ALL BANDS OVERVIEW", font=FTB, bg=BG2, fg=TEXT_DIM).pack(side="left", padx=12, pady=10)
        tk.Button(bar, text="↻ Refresh Overview", command=self.refresh_all_labels, font=FTS,
                  bg=BG3, fg=GREEN, activebackground=BG, activeforeground=GREEN,
                  relief="flat", bd=0, padx=12, pady=4, cursor="hand2").pack(side="right", padx=12, pady=8)

        self._inner, self._canvas = make_scrollframe(self)

    def refresh_all_labels(self):
        for w in self._inner.winfo_children():
            w.destroy()

        if not self.show.bands:
            tk.Label(self._inner, text="No bands to display.", font=FTH, bg=BG, fg=TEXT_DIM).pack(pady=20)
            return

        for band in self.show.bands:
            band_container = tk.Frame(self._inner, bg=BG)
            band_container.pack(fill="x", padx=15, pady=(15, 25))

            # Header
            hdr = tk.Frame(band_container, bg=BG2)
            hdr.pack(fill="x", pady=(0, 10))
            tk.Label(hdr, text=f"BAND: {band.band_name.upper()}", font=FTH, bg=BG2, fg=TEXT).pack(anchor="w", padx=10, pady=8)

            body = tk.Frame(band_container, bg=BG)
            body.pack(fill="x")
            body.columnconfigure(0, weight=3)
            body.columnconfigure(1, weight=0, minsize=14)
            body.columnconfigure(2, weight=2)
            
            # Left side (Stage Boxes)
            sb_frame = tk.Frame(body, bg=BG)
            sb_frame.grid(row=0, column=0, sticky="nsew")
            tk.Label(sb_frame, text="STAGE BOX LABELS", font=FTB, bg=BG, fg=ACCENT).pack(anchor="w", pady=(0, 4))
            
            # Right side (Outputs)
            out_frame = tk.Frame(body, bg=BG)
            out_frame.grid(row=0, column=2, sticky="nsew")
            tk.Label(out_frame, text="OUTPUT LABELS", font=FTB, bg=BG, fg=ACCENT2).pack(anchor="w", pady=(0, 4))

            # Center divider
            tk.Frame(body, bg=BORDER, width=2).grid(row=0, column=1, sticky="ns", padx=10)

            # --- Map Data ---
            patch_map = {}
            for i, ch in enumerate(band.inputs):
                if ch["box"] != "---" and ch["socket"] > 0:
                    patch_map[(ch["box"], ch["socket"])] = (i + 1, ch["name"], "IN")
            for i, ch in enumerate(band.outputs):
                if ch["box"] != "---" and ch["socket"] > 0:
                    patch_map[(ch["box"], ch["socket"])] = (i + 1, ch["name"], "OUT")

            # Build Stage Boxes inside this band
            for bi, box_name in enumerate(band.box_order):
                clr   = band.box_color(box_name)
                bdata = band.boxes[box_name]
                label = bdata.get("name", box_name)

                b_hdr = tk.Frame(sb_frame, bg=clr)
                b_hdr.pack(fill="x", pady=(8, 2), padx=2)
                tk.Label(b_hdr, text=f"  {label}  ({box_name})", font=FTB, bg=clr, fg=DARK_TXT).pack(side="left", padx=6, pady=4)

                grid_f = tk.Frame(sb_frame, bg=BG2)
                grid_f.pack(fill="x", padx=2, pady=(0, 2))

                for si in range(NUM_SOCKETS):
                    snum    = si + 1
                    mode    = bdata["socket_mode"][si]
                    is_flex = snum >= FLEX_START
                    col     = si % 4
                    row_g   = si // 4
                    grid_f.columnconfigure(col, weight=1)

                    cell = tk.Frame(grid_f, bg=BG3)
                    cell.grid(row=row_g, column=col, padx=2, pady=2, sticky="ew")

                    badge_clr = GREEN if mode == "IN" else OUT_CLR
                    tk.Label(cell, text=f"S{snum:02d}", font=FTX, bg=badge_clr, fg=DARK_TXT, width=4).pack(side="left", ipady=3)
                    if is_flex:
                        tk.Label(cell, text=mode, font=FTX, bg=BG3, fg=badge_clr).pack(side="left", padx=2)

                    key = (box_name, snum)
                    if key in patch_map:
                        cnum, cname, kind = patch_map[key]
                        tag_clr = ACCENT if kind == "IN" else ACCENT2
                        prefix  = f"I{cnum:02d}" if kind == "IN" else f"O{cnum:02d}"
                        tk.Label(cell, text=prefix, font=FTX, bg=BG3, fg=tag_clr).pack(side="left", padx=(4, 1))
                        tk.Label(cell, text=cname or "-", font=FT, bg=BG3, fg=TEXT, anchor="w").pack(
                            side="left", padx=2, pady=3, fill="x", expand=True)
                        src_list = band.inputs if kind == "IN" else band.outputs
                        loc = src_list[cnum - 1].get("location", "")
                        if loc:
                            tk.Label(cell, text=f"{loc}", font=FTX, bg=BG3, fg=PURPLE, anchor="w").pack(side="left", padx=(0, 4))
                    else:
                        tk.Label(cell, text="-", font=FTX, bg=BG3, fg=TEXT_DIM, anchor="w").pack(
                            side="left", padx=6, pady=3, fill="x", expand=True)

            # Build Outputs inside this band
            for i, out in enumerate(band.outputs):
                f_bg = BG3 if i % 2 == 0 else BG2
                f  = tk.Frame(out_frame, bg=f_bg)
                f.pack(fill="x", padx=2, pady=1)
                tk.Label(f, text=f"{i+1:02d}", font=FTB, bg=ACCENT2, fg=DARK_TXT, width=4).pack(side="left", padx=(4, 5), pady=4, ipady=1)
                tk.Label(f, text=out["name"] or "-", font=FT, bg=f_bg, fg=TEXT, anchor="w", width=16).pack(side="left", padx=4)
                tk.Label(f, text=out["type"], font=FTS, bg=f_bg, fg=TEXT_DIM, anchor="w", width=10).pack(side="left", padx=2)
                if out["box"] != "---" and out["socket"] > 0:
                    tk.Label(f, text=f"-> {out['box']} S{out['socket']:02d}", font=FTS,
                             bg=f_bg, fg=ACCENT2, anchor="w").pack(side="left", padx=6)
                loc = out.get("location", "")
                if loc:
                    tk.Label(f, text=f" {loc}", font=FTS, bg=f_bg, fg=PURPLE, anchor="w").pack(side="left", padx=6)
        
        self._canvas.update_idletasks()
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))


# ─────────────────────────────────────────────
#  BandPanel  -  full patch UI for ONE band
# ─────────────────────────────────────────────
class BandPanel(tk.Frame):
    def __init__(self, master, app, band: BandData):
        super().__init__(master, bg=BG)
        self.app   = app
        self.band  = band
        self._building = True
        self._updating  = False

        self._build()
        self._building = False
        self._refresh_all()

    def _build(self):
        bar = tk.Frame(self, bg=BG2, height=45)
        bar.pack(fill="x")
        tk.Label(bar, text="  BAND NAME:", font=FTB, bg=BG2, fg=TEXT_DIM).pack(side="left", padx=(8, 4), pady=10)

        self._band_name_var = tk.StringVar(value=self.band.band_name)
        tk.Entry(bar, textvariable=self._band_name_var, font=FTB,
                 bg=BG3, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=0, width=25).pack(side="left", ipady=4, pady=6)

        def _on_name_change(*_):
            self.band.band_name = self._band_name_var.get()
            self.app.rename_band_tab(self)
        self._band_name_var.trace_add("write", _on_name_change)

        tk.Button(bar, text="✖ Remove Band", command=lambda: self.app.remove_band_panel(self),
                  font=FTS, bg=BG2, fg=RED, activebackground=BG, activeforeground=RED,
                  relief="flat", bd=0, padx=10, cursor="hand2").pack(side="right", padx=8, pady=6)

        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=6, pady=(4, 6))

        self._tab_inputs  = tk.Frame(self._nb, bg=BG)
        self._tab_outputs = tk.Frame(self._nb, bg=BG)
        self._tab_boxes   = tk.Frame(self._nb, bg=BG)
        self._tab_labels  = tk.Frame(self._nb, bg=BG)

        self._nb.add(self._tab_inputs,  text="  Inputs (52)  ")
        self._nb.add(self._tab_outputs, text="  Outputs (24)  ")
        self._nb.add(self._tab_boxes,   text="  Stage Boxes  ")
        self._nb.add(self._tab_labels,  text="  Label View  ")

        self._build_inputs_tab()
        self._build_outputs_tab()
        self._build_boxes_tab()
        self._build_labels_tab()

        self._nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

    # ═══════════════════════════════════════════
    #  INPUTS TAB
    # ═══════════════════════════════════════════
    def _build_inputs_tab(self):
        tab = self._tab_inputs
        bar = tk.Frame(tab, bg=BG2, height=38)
        bar.pack(fill="x")
        tk.Label(bar, text="  INPUT PATCH  - 52 Channels",
                 font=FTB, bg=BG2, fg=TEXT_DIM).pack(side="left", padx=12, pady=8)
        for txt, cmd, fg in [
            ("✖ Clear All",  self._clear_inputs,      RED),
            ("⚡ Auto-Name",  self._autonumber_inputs,  YELLOW),
        ]:
            tk.Button(bar, text=txt, command=cmd, font=FTS,
                      bg=BG2, fg=fg, activebackground=BG, activeforeground=fg,
                      relief="flat", bd=0, padx=10, cursor="hand2").pack(side="right", padx=6, pady=6)

        _, _, inner = make_scrollable(tab)

        hrow = tk.Frame(inner, bg=BG2)
        hrow.pack(fill="x", pady=(0, 2))
        for txt, w in [(" CH", 4), ("CHANNEL NAME", 26), ("STAGE BOX", 12),
                       ("SOCKET", 7), ("DIR", 4), ("LOCATION", 15), ("NOTE", 18)]:
            tk.Label(hrow, text=txt, font=FTS, bg=BG2, fg=TEXT_DIM,
                     width=w, anchor="w").pack(side="left", padx=4, pady=4)

        self._input_rows = []
        for i in range(NUM_INPUTS):
            self._input_rows.append(self._make_input_row(inner, i))

    def _make_input_row(self, parent, idx):
        d  = self.band.inputs[idx]
        bg = BG3 if idx % 2 == 0 else BG2

        frame = tk.Frame(parent, bg=bg)
        frame.pack(fill="x", padx=2, pady=1)

        ch_badge = tk.Label(frame, text=f"{idx+1:02d}", font=FTB,
                             bg=TEXT_DIM, fg=DARK_TXT, width=4, anchor="center")
        ch_badge.pack(side="left", padx=(4, 5), pady=3, ipady=2)

        name_var = tk.StringVar(value=d["name"])
        tk.Entry(frame, textvariable=name_var, font=FT,
                 bg=BG, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=0, width=22).pack(side="left", padx=4, pady=3, ipady=3)

        box_var = tk.StringVar(value=d["box"])
        box_cb  = ttk.Combobox(frame, textvariable=box_var, values=self.band.box_choices(),
                                state="readonly", width=7, font=FT)
        box_cb.pack(side="left", padx=4, pady=3)

        socket_var = tk.StringVar(value="none" if d["socket"] == 0 else str(d["socket"]))
        socket_cb  = ttk.Combobox(frame, textvariable=socket_var,
                                   state="readonly", width=5, font=FT)
        socket_cb.pack(side="left", padx=4, pady=3)

        dir_lbl = tk.Label(frame, text="", font=FTX, bg=bg, fg=TEXT_DIM, width=4, anchor="center")
        dir_lbl.pack(side="left", padx=2, pady=3)

        location_var = tk.StringVar(value=d.get("location", ""))
        tk.Entry(frame, textvariable=location_var, font=FTS,
                 bg=BG, fg=PURPLE, insertbackground=PURPLE,
                 relief="flat", bd=0, width=14).pack(side="left", padx=4, pady=3, ipady=3)

        note_var = tk.StringVar(value=d["note"])
        tk.Entry(frame, textvariable=note_var, font=FTS,
                 bg=BG, fg=TEXT_DIM, insertbackground=TEXT,
                 relief="flat", bd=0, width=18).pack(side="left", padx=4, pady=3, ipady=3, fill="x", expand=True)

        row = {"name": name_var, "box": box_var, "box_cb": box_cb, "socket": socket_var,
               "socket_cb": socket_cb, "dir_lbl": dir_lbl,
               "location": location_var, "note": note_var,
               "frame": frame, "bg": bg, "ch_badge": ch_badge}

        def _refresh_sockets(*_, r=row, i=idx):
            if self._building or self._updating: return
            self._fill_input_sockets(r)
            self._sync_input_data(r, i)
            self._update_input_badge_color(r)

        def _on_socket(*_, r=row, i=idx):
            if self._building or self._updating: return
            self._sync_input_data(r, i)
            self._update_dir(r)

        def _on_name_note(*_, r=row, i=idx):
            if self._building or self._updating: return
            self._sync_input_data(r, i)

        box_var.trace_add("write", _refresh_sockets)
        socket_var.trace_add("write", _on_socket)
        name_var.trace_add("write", _on_name_note)
        location_var.trace_add("write", _on_name_note)
        note_var.trace_add("write", _on_name_note)

        self._fill_input_sockets(row)
        self._update_dir(row)
        return row

    def _fill_input_sockets(self, row):
        box = row["box"].get()
        cur = row["socket"].get()
        opts = ["none"]
        if box in self.band.boxes:
            for s in range(1, NUM_SOCKETS + 1):
                if self.band.get_socket_mode(box, s) != "IN": continue
                if not self.band.is_socket_assigned(box, s) or str(s) == cur:
                    opts.append(str(s))
        row["socket_cb"]["values"] = opts
        row["socket_cb"].set(cur if cur in opts else "none")

    def _sync_input_data(self, row, idx):
        if self._updating: return
        self._updating = True
        try:
            sv       = row["socket"].get()
            new_box  = row["box"].get()
            new_sock = 0 if sv == "none" else int(sv)

            old_box  = self.band.inputs[idx]["box"]
            old_sock = self.band.inputs[idx]["socket"]
            if old_box != "---" and old_sock > 0:
                self.band.set_socket_assigned(old_box, old_sock, False)

            self.band.inputs[idx]["name"]     = row["name"].get()
            self.band.inputs[idx]["box"]      = new_box
            self.band.inputs[idx]["socket"]   = new_sock
            self.band.inputs[idx]["location"] = row["location"].get()
            self.band.inputs[idx]["note"]     = row["note"].get()

            if new_box != "---" and new_sock > 0:
                self.band.set_socket_assigned(new_box, new_sock, True)
            self._refresh_all_socket_dropdowns(exclude_input=idx)
        finally:
            self._updating = False

    def _update_dir(self, row):
        box = row["box"].get()
        sv  = row["socket"].get()
        lbl = row["dir_lbl"]
        bg  = row["bg"]
        if box == "---" or sv == "none":
            lbl.config(text="", bg=bg)
            return
        mode = self.band.get_socket_mode(box, int(sv))
        lbl.config(text=mode, fg=GREEN if mode == "IN" else OUT_CLR, bg=bg)

    def _update_input_badge_color(self, row):
        badge = row.get("ch_badge")
        if badge is None: return
        box = row["box"].get()
        clr = self.band.box_color(box) if box in self.band.box_order else TEXT_DIM
        badge.config(bg=clr)

    def _update_output_badge_color(self, row):
        badge = row.get("ch_badge")
        if badge is None: return
        box = row["box"].get()
        clr = self.band.box_color(box) if box in self.band.box_order else ACCENT2
        badge.config(bg=clr)

    # ═══════════════════════════════════════════
    #  OUTPUTS TAB
    # ═══════════════════════════════════════════
    def _build_outputs_tab(self):
        tab = self._tab_outputs
        bar = tk.Frame(tab, bg=BG2, height=38)
        bar.pack(fill="x")
        tk.Label(bar, text="  OUTPUT PATCH  - 24 Channels", font=FTB, bg=BG2, fg=TEXT_DIM).pack(side="left", padx=12, pady=8)
        tk.Button(bar, text="✖ Clear All", command=self._clear_outputs, font=FTS,
                  bg=BG2, fg=RED, activebackground=BG, activeforeground=RED,
                  relief="flat", bd=0, padx=10, cursor="hand2").pack(side="right", padx=8, pady=6)

        _, _, inner = make_scrollable(tab)

        hrow = tk.Frame(inner, bg=BG2)
        hrow.pack(fill="x", pady=(0, 2))
        for txt, w in [(" OUT", 4), ("OUTPUT NAME", 22), ("TYPE", 12),
                       ("STAGE BOX", 9), ("SOCKET", 7), ("LOCATION", 14), ("NOTE", 18)]:
            tk.Label(hrow, text=txt, font=FTS, bg=BG2, fg=TEXT_DIM, width=w, anchor="w").pack(side="left", padx=4, pady=4)

        self._output_rows = []
        for i in range(NUM_OUTPUTS):
            self._output_rows.append(self._make_output_row(inner, i))

    def _make_output_row(self, parent, idx):
        d  = self.band.outputs[idx]
        bg = BG3 if idx % 2 == 0 else BG2

        frame = tk.Frame(parent, bg=bg)
        frame.pack(fill="x", padx=2, pady=1)

        ch_badge = tk.Label(frame, text=f"{idx+1:02d}", font=FTB, bg=ACCENT2, fg=DARK_TXT, width=4, anchor="center")
        ch_badge.pack(side="left", padx=(4, 5), pady=3, ipady=2)

        name_var = tk.StringVar(value=d["name"])
        tk.Entry(frame, textvariable=name_var, font=FT, bg=BG, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=0, width=22).pack(side="left", padx=4, pady=3, ipady=3)

        type_var = tk.StringVar(value=d["type"])
        ttk.Combobox(frame, textvariable=type_var, values=OUTPUT_TYPES, state="readonly", width=10, font=FT).pack(side="left", padx=4, pady=3)

        box_var = tk.StringVar(value=d["box"])
        box_cb  = ttk.Combobox(frame, textvariable=box_var, values=self.band.box_choices(), state="readonly", width=7, font=FT)
        box_cb.pack(side="left", padx=4, pady=3)

        socket_var = tk.StringVar(value="none" if d["socket"] == 0 else str(d["socket"]))
        socket_cb  = ttk.Combobox(frame, textvariable=socket_var, state="readonly", width=5, font=FT)
        socket_cb.pack(side="left", padx=4, pady=3)

        location_var = tk.StringVar(value=d.get("location", ""))
        tk.Entry(frame, textvariable=location_var, font=FTS, bg=BG, fg=PURPLE, insertbackground=PURPLE,
                 relief="flat", bd=0, width=14).pack(side="left", padx=4, pady=3, ipady=3)

        note_var = tk.StringVar(value=d["note"])
        tk.Entry(frame, textvariable=note_var, font=FTS, bg=BG, fg=TEXT_DIM, insertbackground=TEXT,
                 relief="flat", bd=0, width=18).pack(side="left", padx=4, pady=3, ipady=3, fill="x", expand=True)

        row = {"name": name_var, "type": type_var, "box": box_var, "box_cb": box_cb,
               "socket": socket_var, "socket_cb": socket_cb,
               "location": location_var, "note": note_var, "bg": bg, "ch_badge": ch_badge}

        def _refresh_sockets(*_, r=row, i=idx):
            if self._building or self._updating: return
            self._fill_output_sockets(r)
            self._sync_output_data(r, i)
            self._update_output_badge_color(r)

        def _on_rest(*_, r=row, i=idx):
            if self._building or self._updating: return
            self._sync_output_data(r, i)

        box_var.trace_add("write", _refresh_sockets)
        socket_var.trace_add("write", _on_rest)
        name_var.trace_add("write", _on_rest)
        type_var.trace_add("write", _on_rest)
        location_var.trace_add("write", _on_rest)
        note_var.trace_add("write", _on_rest)

        self._fill_output_sockets(row)
        return row

    def _fill_output_sockets(self, row):
        box = row["box"].get()
        cur = row["socket"].get()
        opts = ["none"]
        if box in self.band.boxes:
            for s in range(1, NUM_SOCKETS + 1):
                if self.band.get_socket_mode(box, s) != "OUT": continue
                if not self.band.is_socket_assigned(box, s) or str(s) == cur:
                    opts.append(str(s))
        row["socket_cb"]["values"] = opts
        row["socket_cb"].set(cur if cur in opts else "none")

    def _sync_output_data(self, row, idx):
        if self._updating: return
        self._updating = True
        try:
            sv       = row["socket"].get()
            new_box  = row["box"].get()
            new_sock = 0 if sv == "none" else int(sv)

            old_box  = self.band.outputs[idx]["box"]
            old_sock = self.band.outputs[idx]["socket"]
            if old_box != "---" and old_sock > 0:
                self.band.set_socket_assigned(old_box, old_sock, False)

            self.band.outputs[idx]["name"]     = row["name"].get()
            self.band.outputs[idx]["type"]     = row["type"].get()
            self.band.outputs[idx]["box"]      = new_box
            self.band.outputs[idx]["socket"]   = new_sock
            self.band.outputs[idx]["location"] = row["location"].get()
            self.band.outputs[idx]["note"]     = row["note"].get()

            if new_box != "---" and new_sock > 0:
                self.band.set_socket_assigned(new_box, new_sock, True)

            self._refresh_all_socket_dropdowns(exclude_output=idx)
        finally:
            self._updating = False

    # ═══════════════════════════════════════════
    #  STAGE BOXES TAB
    # ═══════════════════════════════════════════
    def _refresh_all_socket_dropdowns(self, exclude_input=None, exclude_output=None):
        if self._building or self._updating: return
        self._updating = True
        try:
            for i, row in enumerate(getattr(self, "_input_rows", [])):
                if i != exclude_input:
                    self._fill_input_sockets(row)
                    self._update_dir(row)
            for i, row in enumerate(getattr(self, "_output_rows", [])):
                if i != exclude_output:
                    self._fill_output_sockets(row)
            if hasattr(self, "_patch_labels"):
                self._refresh_box_patch_labels()
        finally:
            self._updating = False

    def _on_socket_mode_change(self):
        for row in self._input_rows:
            self._fill_input_sockets(row)
            self._update_dir(row)
        for row in self._output_rows:
            self._fill_output_sockets(row)
        self._refresh_box_patch_labels()

    def _refresh_box_patch_labels(self):
        lookup = {}
        for i, ch in enumerate(self.band.inputs):
            if ch["box"] != "---" and ch["socket"] > 0:
                lookup[(ch["box"], ch["socket"])] = (f"I{i+1:02d} {ch['name']}", ACCENT)
        for i, ch in enumerate(self.band.outputs):
            if ch["box"] != "---" and ch["socket"] > 0:
                lookup[(ch["box"], ch["socket"])] = (f"O{i+1:02d} {ch['name']}", ACCENT2)

        for (box, snum), widget in self._patch_labels.items():
            if (box, snum) in lookup:
                txt, clr = lookup[(box, snum)]
                widget.config(text=txt, fg=clr)
            else:
                widget.config(text="", fg=TEXT_DIM)

    def _build_boxes_tab(self):
        self._patch_labels = {}
        tab = self._tab_boxes
        bar = tk.Frame(tab, bg=BG2, height=38)
        bar.pack(fill="x")
        tk.Label(bar, text="  STAGE BOX CONFIG  -  Sockets 1-8: fixed IN  |  Sockets 9-12: toggle IN / OUT",
                 font=FTB, bg=BG2, fg=TEXT_DIM).pack(side="left", padx=12, pady=8)
        tk.Button(bar, text=" ✚ Add Stage Box", command=self._add_stage_box, font=FTS,
                  bg=BG2, fg=GREEN, activebackground=BG, activeforeground=GREEN,
                  relief="flat", bd=0, padx=10, cursor="hand2").pack(side="right", padx=8, pady=6)

        _, canvas, inner = make_scrollable(tab, horizontal=True)

        COLS = 4
        for bi, box_name in enumerate(self.band.box_order):
            col       = bi % COLS
            row_start = (bi // COLS) * 15
            clr       = self.band.box_color(box_name)
            inner.columnconfigure(col, weight=1)

            hdr = tk.Frame(inner, bg=clr)
            hdr.grid(row=row_start, column=col, padx=8, pady=(14, 2), sticky="ew")
            bname_var = tk.StringVar(value=self.band.boxes[box_name]["name"])
            tk.Entry(hdr, textvariable=bname_var, font=FTB, bg=clr, fg=DARK_TXT, insertbackground=DARK_TXT,
                     relief="flat", bd=0, width=12).pack(side="left", padx=8, pady=5)
            tk.Label(hdr, text=f"({box_name})", font=FTX, bg=clr, fg=DARK_TXT).pack(side="left")

            def _save_name(*_, bn=box_name, v=bname_var):
                self.band.boxes[bn]["name"] = v.get()
            bname_var.trace_add("write", _save_name)

            for si in range(NUM_SOCKETS):
                snum    = si + 1
                is_flex = snum >= FLEX_START
                mode    = self.band.boxes[box_name]["socket_mode"][si]
                sf_bg   = BG3 if si % 2 == 0 else BG2

                sf = tk.Frame(inner, bg=sf_bg)
                sf.grid(row=row_start + 1 + si, column=col, padx=8, pady=1, sticky="ew")

                badge_clr = GREEN if mode == "IN" else OUT_CLR
                sn_lbl = tk.Label(sf, text=f"S{snum:02d}", font=FTX, bg=badge_clr, fg=DARK_TXT, width=4)
                sn_lbl.pack(side="left", ipady=3)

                if is_flex:
                    mode_var = tk.StringVar(value=mode)
                    btn = tk.Button(sf, text=mode, font=FTX, width=4, bg=badge_clr, fg=DARK_TXT,
                                     relief="flat", bd=0, cursor="hand2")

                    def _make_toggle(bn=box_name, sn=snum, mv=mode_var, b=btn, sl=sn_lbl):
                        def toggle(_=None):
                            new = "OUT" if mv.get() == "IN" else "IN"
                            nc  = GREEN if new == "IN" else OUT_CLR
                            mv.set(new)
                            b.config(text=new, bg=nc, fg=DARK_TXT)
                            sl.config(bg=nc, fg=DARK_TXT)
                            self.band.set_socket_mode(bn, sn, new)
                            self._on_socket_mode_change()
                        return toggle

                    btn.config(command=_make_toggle())
                    btn.pack(side="left", padx=6, pady=3, ipady=1)
                else:
                    tk.Label(sf, text="IN", font=FTX, bg=sf_bg, fg=GREEN).pack(side="left", padx=8)

                pl = tk.Label(sf, text="", font=FTX, bg=sf_bg, fg=TEXT_DIM, anchor="w")
                pl.pack(side="left", padx=4, fill="x", expand=True)
                self._patch_labels[(box_name, snum)] = pl

        self.after(150, self._refresh_box_patch_labels)

    def _add_stage_box(self):
        letter = self.band.add_box()
        if letter is None:
            messagebox.showinfo("Stage Boxes", "Maximum of 26 stage boxes (A-Z) reached.")
            return

        choices = self.band.box_choices()
        for row in self._input_rows:
            row["box_cb"]["values"] = choices
        for row in self._output_rows:
            row["box_cb"]["values"] = choices

        for w in self._tab_boxes.winfo_children():
            w.destroy()
        self._build_boxes_tab()

    # ═══════════════════════════════════════════
    #  LOCAL LABEL VIEW TAB
    # ═══════════════════════════════════════════
    def _build_labels_tab(self):
        tab = self._tab_labels
        bar = tk.Frame(tab, bg=BG2, height=38)
        bar.pack(fill="x")
        tk.Label(bar, text="  LOCAL LABEL OVERVIEW", font=FTB, bg=BG2, fg=TEXT_DIM).pack(side="left", padx=12, pady=8)
        tk.Button(bar, text="↻ Refresh", command=self._refresh_labels, font=FTS,
                  bg=BG3, fg=GREEN, activebackground=BG, activeforeground=GREEN,
                  relief="flat", bd=0, padx=10, cursor="hand2").pack(side="right", padx=8, pady=6)

        body = tk.Frame(tab, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=8)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=0, minsize=14)
        body.columnconfigure(2, weight=2)
        body.rowconfigure(0, weight=1)

        sb_frame = tk.Frame(body, bg=BG)
        sb_frame.grid(row=0, column=0, sticky="nsew")
        tk.Label(sb_frame, text="STAGE BOX LABELS", font=FTB, bg=BG, fg=ACCENT).pack(anchor="w", pady=(0, 6))
        sb_c, self._sb_canvas = make_scrollframe(sb_frame)
        self._sb_inner = sb_c

        tk.Frame(body, bg=BORDER, width=2).grid(row=0, column=1, sticky="ns", padx=6)

        out_frame = tk.Frame(body, bg=BG)
        out_frame.grid(row=0, column=2, sticky="nsew")
        tk.Label(out_frame, text="OUTPUT LABELS", font=FTB, bg=BG, fg=ACCENT2).pack(anchor="w", pady=(0, 6))
        out_c, self._out_canvas = make_scrollframe(out_frame)
        self._out_inner = out_c

    def _refresh_labels(self):
        for w in self._sb_inner.winfo_children(): w.destroy()

        patch_map = {}
        for i, ch in enumerate(self.band.inputs):
            if ch["box"] != "---" and ch["socket"] > 0:
                patch_map[(ch["box"], ch["socket"])] = (i + 1, ch["name"], "IN")
        for i, ch in enumerate(self.band.outputs):
            if ch["box"] != "---" and ch["socket"] > 0:
                patch_map[(ch["box"], ch["socket"])] = (i + 1, ch["name"], "OUT")

        for bi, box_name in enumerate(self.band.box_order):
            clr   = self.band.box_color(box_name)
            bdata = self.band.boxes[box_name]
            label = bdata.get("name", box_name)

            hdr = tk.Frame(self._sb_inner, bg=clr)
            hdr.pack(fill="x", pady=(10, 2), padx=2)
            tk.Label(hdr, text=f"  {label}  ({box_name})", font=FTB, bg=clr, fg=DARK_TXT).pack(side="left", padx=6, pady=4)

            grid_f = tk.Frame(self._sb_inner, bg=BG2)
            grid_f.pack(fill="x", padx=2, pady=(0, 2))

            for si in range(NUM_SOCKETS):
                snum    = si + 1
                mode    = bdata["socket_mode"][si]
                is_flex = snum >= FLEX_START
                col     = si % 4
                row_g   = si // 4
                grid_f.columnconfigure(col, weight=1)

                cell = tk.Frame(grid_f, bg=BG3)
                cell.grid(row=row_g, column=col, padx=2, pady=2, sticky="ew")

                badge_clr = GREEN if mode == "IN" else OUT_CLR
                tk.Label(cell, text=f"S{snum:02d}", font=FTX, bg=badge_clr, fg=DARK_TXT, width=4).pack(side="left", ipady=3)
                if is_flex:
                    tk.Label(cell, text=mode, font=FTX, bg=BG3, fg=badge_clr).pack(side="left", padx=2)

                key = (box_name, snum)
                if key in patch_map:
                    cnum, cname, kind = patch_map[key]
                    tag_clr = ACCENT if kind == "IN" else ACCENT2
                    prefix  = f"I{cnum:02d}" if kind == "IN" else f"O{cnum:02d}"
                    tk.Label(cell, text=prefix, font=FTX, bg=BG3, fg=tag_clr).pack(side="left", padx=(4, 1))
                    tk.Label(cell, text=cname or "-", font=FT, bg=BG3, fg=TEXT, anchor="w").pack(
                        side="left", padx=2, pady=3, fill="x", expand=True)
                    src_list = self.band.inputs if kind == "IN" else self.band.outputs
                    loc = src_list[cnum - 1].get("location", "")
                    if loc:
                        tk.Label(cell, text=f"{loc}", font=FTX, bg=BG3, fg=PURPLE, anchor="w").pack(side="left", padx=(0, 4))
                else:
                    tk.Label(cell, text="-", font=FTX, bg=BG3, fg=TEXT_DIM, anchor="w").pack(
                        side="left", padx=6, pady=3, fill="x", expand=True)

        self._sb_canvas.update_idletasks()
        self._sb_canvas.configure(scrollregion=self._sb_canvas.bbox("all"))

        for w in self._out_inner.winfo_children(): w.destroy()

        for i, out in enumerate(self.band.outputs):
            bg = BG3 if i % 2 == 0 else BG2
            f  = tk.Frame(self._out_inner, bg=bg)
            f.pack(fill="x", padx=2, pady=1)
            tk.Label(f, text=f"{i+1:02d}", font=FTB, bg=ACCENT2, fg=DARK_TXT, width=4).pack(side="left", padx=(4, 5), pady=4, ipady=1)
            tk.Label(f, text=out["name"] or "-", font=FT, bg=bg, fg=TEXT, anchor="w", width=16).pack(side="left", padx=4)
            tk.Label(f, text=out["type"], font=FTS, bg=bg, fg=TEXT_DIM, anchor="w", width=10).pack(side="left", padx=2)
            if out["box"] != "---" and out["socket"] > 0:
                tk.Label(f, text=f"-> {out['box']} S{out['socket']:02d}", font=FTS,
                         bg=bg, fg=ACCENT2, anchor="w").pack(side="left", padx=6)
            loc = out.get("location", "")
            if loc:
                tk.Label(f, text=f" {loc}", font=FTS, bg=bg, fg=PURPLE, anchor="w").pack(side="left", padx=6)

        self._out_canvas.update_idletasks()
        self._out_canvas.configure(scrollregion=self._out_canvas.bbox("all"))

    # ═══════════════════════════════════════════
    #  Tab change / refresh
    # ═══════════════════════════════════════════
    def _on_tab_change(self, _):
        idx = self._nb.index(self._nb.select())
        if idx == 2:
            self._refresh_box_patch_labels()
        elif idx == 3:
            self._refresh_labels()

    def _refresh_all(self):
        self._updating = True
        try:
            self.band.rebuild_assigned_from_data()
            for i, row in enumerate(self._input_rows):
                d = self.band.inputs[i]
                row["name"].set(d["name"])
                row["box"].set(d["box"])
                row["location"].set(d.get("location", ""))
                row["note"].set(d["note"])
                self._fill_input_sockets(row)
                row["socket"].set("none" if d["socket"] == 0 else str(d["socket"]))
                self._update_dir(row)
                self._update_input_badge_color(row)
            for i, row in enumerate(self._output_rows):
                d = self.band.outputs[i]
                row["name"].set(d["name"])
                row["type"].set(d["type"])
                row["box"].set(d["box"])
                row["location"].set(d.get("location", ""))
                row["note"].set(d["note"])
                self._fill_output_sockets(row)
                row["socket"].set("none" if d["socket"] == 0 else str(d["socket"]))
                self._update_output_badge_color(row)
            self._band_name_var.set(self.band.band_name)
        finally:
            self._updating = False

    def _clear_inputs(self):
        if messagebox.askyesno("Clear Inputs", "Clear all 52 input channels for this band?"):
            for i in range(NUM_INPUTS):
                self.band.inputs[i] = {"name": "", "box": "---", "socket": 0, "location": "", "note": ""}
            self.band.rebuild_assigned_from_data()
            self._refresh_all()

    def _clear_outputs(self):
        if messagebox.askyesno("Clear Outputs", "Clear all 24 output channels for this band?"):
            for i in range(NUM_OUTPUTS):
                self.band.outputs[i] = {"name": "", "type": "---", "box": "---", "socket": 0, "location": "", "note": ""}
            self.band.rebuild_assigned_from_data()
            self._refresh_all()

    def _autonumber_inputs(self):
        for i, row in enumerate(self._input_rows):
            if not row["name"].get():
                row["name"].set(f"Input {i+1:02d}")


# ─────────────────────────────────────────────
#  App  -  the whole Show window 
# ─────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.show = ShowData()
        self._band_panels = []
        self.all_labels_panel = None

        self.title("Stage Box & Audio Patch Manager")
        self.configure(bg=BG)
        self.geometry("1500x950")

        self._apply_style()
        self._build_ui()

    def _apply_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        
        s.configure(".",
            background=BG, foreground=TEXT, fieldbackground=BG3,
            troughcolor=BG2, bordercolor=BORDER, lightcolor=BORDER,
            darkcolor=BORDER, font=FT, borderwidth=0)
            
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", background=BG2, foreground=TEXT_DIM, padding=[20, 10], font=FTB, borderwidth=0)
        s.map("TNotebook.Tab",
            background=[("selected", BG3)], foreground=[("selected", ACCENT)])
            
        s.configure("TCombobox",
            selectbackground=BG2, selectforeground=TEXT,
            background=BG3, foreground=TEXT, arrowcolor=ACCENT, borderwidth=0)
        s.map("TCombobox",
            fieldbackground=[("readonly", BG3)], foreground=[("readonly", TEXT)])
            
        for o in ("Vertical", "Horizontal"):
            s.configure(f"{o}.TScrollbar",
                gripcount=0, background=BG3, troughcolor=BG,
                arrowcolor=TEXT_DIM, borderwidth=0)

    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG2, height=65)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="PATCH MANAGER", font=FTTL, bg=BG2, fg=ACCENT).pack(side="left", padx=25, pady=10)

        self._show_var = tk.StringVar(value=self.show.show_name)
        self._show_var.trace_add("write", lambda *_: setattr(self.show, "show_name", self._show_var.get()))
        tk.Label(hdr, text="SHOW:", font=FTS, bg=BG2, fg=TEXT_DIM).pack(side="left", padx=(20, 8))
        tk.Entry(hdr, textvariable=self._show_var, font=FTB,
                 bg=BG3, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=0, width=28).pack(side="left", ipady=5)

        for txt, cmd, fg in [
            ("💾 SAVE",  self._save,       GREEN),
            ("📂 LOAD",  self._load,       YELLOW),
            ("🖨️ PRINT", self._export_txt, ACCENT),
        ]:
            tk.Button(hdr, text=txt, command=cmd, font=FTB,
                      bg=BG3, fg=fg, activebackground=BG, activeforeground=fg,
                      relief="flat", bd=0, padx=16, pady=6, cursor="hand2").pack(side="right", padx=6, pady=12)

        tk.Button(hdr, text="✚ ADD BAND", command=self._add_band, font=FTB,
                  bg=BG3, fg=GREEN, activebackground=BG, activeforeground=GREEN,
                  relief="flat", bd=0, padx=16, pady=6, cursor="hand2").pack(side="right", padx=10, pady=12)

        self._band_nb = ttk.Notebook(self)
        self._band_nb.pack(fill="both", expand=True, padx=10, pady=(10, 10))
        
        self._band_nb.bind("<<NotebookTabChanged>>", self._on_main_tab_change)

        self._rebuild_band_tabs()

    def _rebuild_band_tabs(self):
        for tab_id in self._band_nb.tabs():
            self._band_nb.forget(tab_id)
            
        self._band_panels = []
        for i, band in enumerate(self.show.bands):
            panel = BandPanel(self._band_nb, self, band)
            self._band_nb.add(panel, text=f"  {band.band_name}  ")
            self._band_panels.append(panel)

        self.all_labels_panel = AllLabelsPanel(self._band_nb, self, self.show)
        self._band_nb.add(self.all_labels_panel, text="  🌍 ALL LABELS OVERVIEW  ")

    def rename_band_tab(self, panel):
        idx = self._band_panels.index(panel)
        self._band_nb.tab(idx, text=f"  {panel.band.band_name}  ")

    def _add_band(self):
        suggested = f"Band {len(self.show.bands) + 1}"
        name = simpledialog.askstring("Add Band", "Band name:", initialvalue=suggested, parent=self)
        if name is None: return
        name = name.strip() or suggested
        self.show.add_band(name)
        self._rebuild_band_tabs()
        self._band_nb.select(len(self._band_panels) - 1)

    def remove_band_panel(self, panel):
        if len(self.show.bands) <= 1:
            messagebox.showwarning("Remove Band", "At least one band must remain.")
            return
        idx = self._band_panels.index(panel)
        if messagebox.askyesno("Remove Band", f"Remove '{panel.band.band_name}' and all of its patch data?"):
            self.show.remove_band(idx)
            self._rebuild_band_tabs()
            
    def _on_main_tab_change(self, _):
        idx = self._band_nb.index(self._band_nb.select())
        if idx == len(self._band_panels): 
            self.all_labels_panel.refresh_all_labels()

    def _save(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Patch File", "*.json"), ("All Files", "*.*")],
            title="Save Patch File",
            initialfile=f"{self.show.show_name.replace(' ','_')}.json")
        if not path: return
        with open(path, "w") as f:
            json.dump(self.show.to_dict(), f, indent=2)
        messagebox.showinfo("Saved", f"Show saved:\n{path}")

    def _load(self):
        path = filedialog.askopenfilename(
            filetypes=[("Patch File", "*.json"), ("All Files", "*.*")],
            title="Load Patch File")
        if not path: return
        with open(path) as f:
            d = json.load(f)
        self.show.from_dict(d)
        self._show_var.set(self.show.show_name)
        self._rebuild_band_tabs()
        messagebox.showinfo("Loaded", f"Show loaded:\n{path}")

    def _export_txt(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text File", "*.txt"), ("All Files", "*.*")],
            title="Export Patch List",
            initialfile=f"{self.show.show_name.replace(' ','_')}_patch.txt")
        if not path: return

        w = 88
        lines = [f"PATCH LIST - {self.show.show_name}",
                 f"Bands in this show: {len(self.show.bands)}",
                 "#" * w, ""]
        for band in self.show.bands:
            lines += build_band_report_lines(band, width=w)
            lines += ["", "#" * w, ""]

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        messagebox.showinfo("Exported", f"Patch list exported for {len(self.show.bands)} band(s):\n{path}")


# ─────────────────────────────────────────────
if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        print(f"Error starting application: {e}")