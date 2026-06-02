"""
Stage Box & Audio Patch Manager
--------------------------------
52 Input channels  |  24 Output channels
Each stage box has 12 sockets:
  - Sockets  1-8  : fixed INPUTS
  - Sockets  9-12 : switchable INPUT or OUTPUT (per socket, toggled in Stage Boxes tab)
Channels select which box + which socket they are patched to.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json

# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────
NUM_INPUTS      = 52
NUM_OUTPUTS     = 24
NUM_SOCKETS     = 12
FIXED_IN_COUNT  = 8           # sockets 1-8 always IN
FLEX_START      = 9           # sockets 9-12 are switchable

STAGE_BOX_NAMES = [f"{c}" for c in "ABCDEFGJ"]   # SB-A  SB-G
BOX_CHOICES     = ["---"] + STAGE_BOX_NAMES

OUTPUT_TYPES = ["---", "Aux", "Auto-Tune IN", "Record", "Other"]

# ─────────────────────────────────────────────
#  Data Model
# ─────────────────────────────────────────────
def _default_box(name):
    return {
        "name":          name,
        "socket_mode":   ["IN"] * NUM_SOCKETS,   # index 0 = socket 1
        # isAssigned per socket: True when a channel is patched to it
        "socket_assigned": {s: False for s in range(1, NUM_SOCKETS + 1)},
    }

class PatchData:
    def __init__(self):
        self.inputs  = [{"name": "", "box": "---", "socket": 0, "note": "", "location": ""}
                        for _ in range(NUM_INPUTS)]
        self.outputs = [{"name": "", "type": "---", "box": "---", "socket": 0, "note": "", "location": ""}
                        for _ in range(NUM_OUTPUTS)]
        self.boxes   = {n: _default_box(n) for n in STAGE_BOX_NAMES}
        self.show_name = "Untitled Show"
        self._building = False

    def get_socket_mode(self, box_name, socket_num):
        if box_name not in self.boxes:
            return "IN"
        return self.boxes[box_name]["socket_mode"][socket_num - 1]

    def set_socket_mode(self, box_name, socket_num, mode):
        if box_name in self.boxes and socket_num >= FLEX_START:
            self.boxes[box_name]["socket_mode"][socket_num - 1] = mode

    def is_socket_assigned(self, box_name, socket_num):
        """Return True if this socket is already used by any channel."""
        if box_name not in self.boxes:
            return False
        return self.boxes[box_name]["socket_assigned"].get(socket_num, False)

    def set_socket_assigned(self, box_name, socket_num, value: bool):
        """Mark (or unmark) a socket as assigned."""
        if box_name in self.boxes and socket_num >= 1:
            self.boxes[box_name]["socket_assigned"][socket_num] = value

    def rebuild_assigned_from_data(self):
        """Recompute all isAssigned flags from current inputs + outputs.
        Call this after load, clear, or any bulk change."""
        # Reset every socket
        for bd in self.boxes.values():
            bd["socket_assigned"] = {s: False for s in range(1, NUM_SOCKETS + 1)}
        # Mark used sockets
        for ch in self.inputs:
            if ch["box"] != "---" and ch["socket"] > 0:
                self.set_socket_assigned(ch["box"], ch["socket"], True)
        for ch in self.outputs:
            if ch["box"] != "---" and ch["socket"] > 0:
                self.set_socket_assigned(ch["box"], ch["socket"], True)

    def to_dict(self):
        return {"show_name": self.show_name,
                "inputs": self.inputs, "outputs": self.outputs, "boxes": self.boxes}

    def from_dict(self, d):
        self.show_name = d.get("show_name", "Untitled Show")
        raw_inputs  = d.get("inputs",  self.inputs)
        raw_outputs = d.get("outputs", self.outputs)
        # Migrate older saves that lack the location field
        for ch in raw_inputs:
            ch.setdefault("location", "")
        for ch in raw_outputs:
            ch.setdefault("location", "")
        self.inputs  = raw_inputs
        self.outputs = raw_outputs
        for name in STAGE_BOX_NAMES:
            raw = d.get("boxes", {}).get(name)
            if raw:
                self.boxes[name] = raw
                sm = self.boxes[name].get("socket_mode", ["IN"] * NUM_SOCKETS)
                if len(sm) < NUM_SOCKETS:
                    sm += ["IN"] * (NUM_SOCKETS - len(sm))
                for i in range(FIXED_IN_COUNT):   # lock 1-8 to IN
                    sm[i] = "IN"
                self.boxes[name]["socket_mode"] = sm
                # Ensure socket_assigned exists (migrate older saves)
                if "socket_assigned" not in self.boxes[name]:
                    self.boxes[name]["socket_assigned"] = {s: False for s in range(1, NUM_SOCKETS + 1)}
        # Recompute isAssigned from actual patch data
        self.rebuild_assigned_from_data()


# ─────────────────────────────────────────────
#  Theme
# ─────────────────────────────────────────────
# ── Gruvbox Dark palette ─────────────────────
BG        = "#282828"   # hard bg
BG2       = "#32302f"   # soft bg
BG3       = "#3c3836"   # bg1
BORDER    = "#504945"   # bg2

TEXT      = "#ebdbb2"   # fg
TEXT_DIM  = "#928374"   # grey (gruvbox gray)

ACCENT    = "#83a598"   # gruvbox aqua/blue
ACCENT2   = "#fe8019"   # gruvbox orange

GREEN     = "#b8bb26"   # gruvbox green
YELLOW    = "#fabd2f"   # gruvbox yellow
RED       = "#fb4934"   # gruvbox red
PURPLE    = "#d3869b"   # gruvbox purple
OUT_CLR   = "#fe8019"   # gruvbox orange (output sockets)

FT   = ("Courier New", 10)
FTS  = ("Courier New", 9)
FTX  = ("Courier New", 8)
FTB  = ("Courier New", 10, "bold")
FTH  = ("Courier New", 13, "bold")
FTTL = ("Courier New", 17, "bold")

# One distinct Gruvbox colour per box (7 boxes, reuse if more)
BOX_COLORS = [
    "#83a598",   # aqua
    "#b8bb26",   # green
    "#fabd2f",   # yellow
    "#fe8019",   # orange
    "#fb4934",   # red
    "#d3869b",   # purple
    "#8ec07c",   # teal
    "#923175",   # red
    "#9238db",   # purple
    "#319caf",
]


# ─────────────────────────────────────────────
#  App
# ─────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.data = PatchData()
        self._building = True   # Block callbacks during setup
        self._updating = False  # The recursion guard
        
        self.title("Stage Box & Audio Patch Manager")
        self.configure(bg=BG)
        self.geometry("1400x880")
        
        self._apply_style()
        self._build_ui()        # This creates the rows and traces
        
        self._building = False  # Setup finished
        self._refresh_all()     # Initial data fill

    # ── Style ────────────────────────────────
    def _apply_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".",
            background=BG, foreground=TEXT, fieldbackground=BG3,
            troughcolor=BG2, bordercolor=BORDER, lightcolor=BORDER,
            darkcolor=BORDER, font=FT)
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab",
            background=BG2, foreground=TEXT_DIM, padding=[16, 8], font=FTB)
        s.map("TNotebook.Tab",
            background=[("selected", BG3)], foreground=[("selected", ACCENT)])
        s.configure("TCombobox",
            selectbackground=BG3, selectforeground=TEXT,
            background=BG3, foreground=TEXT, arrowcolor=ACCENT, borderwidth=1)
        s.map("TCombobox",
            fieldbackground=[("readonly", BG3)], foreground=[("readonly", TEXT)])
        for o in ("Vertical", "Horizontal"):
            s.configure(f"{o}.TScrollbar",
                gripcount=0, background=BG2, troughcolor=BG,
                arrowcolor=TEXT_DIM, borderwidth=0)

    # ── Root UI ──────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=BG2, height=58)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  PATCH MANAGER", font=FTTL,
                 bg=BG2, fg=ACCENT).pack(side="left", padx=20, pady=10)
        self._show_var = tk.StringVar(value=self.data.show_name)
        self._show_var.trace_add("write",
            lambda *_: setattr(self.data, "show_name", self._show_var.get()))
        tk.Label(hdr, text="SHOW:", font=FTS, bg=BG2, fg=TEXT_DIM).pack(side="left", padx=(14,4))
        tk.Entry(hdr, textvariable=self._show_var, font=FT,
                 bg=BG3, fg=ACCENT2, insertbackground=ACCENT2,
                 relief="flat", bd=0, width=26).pack(side="left", ipady=4)
        for txt, cmd, fg in [
            (" SAVE",  self._save,       GREEN),
            (" LOAD",  self._load,       YELLOW),
            ("  PRINT", self._export_txt, ACCENT),
        ]:
            tk.Button(hdr, text=txt, command=cmd, font=FTS,
                      bg=BG3, fg=fg, activebackground=BG, activeforeground=fg,
                      relief="flat", bd=0, padx=12, pady=5,
                      cursor="hand2").pack(side="right", padx=5, pady=10)

        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=8, pady=(5,8))

        self._tab_inputs  = tk.Frame(self._nb, bg=BG)
        self._tab_outputs = tk.Frame(self._nb, bg=BG)
        self._tab_boxes   = tk.Frame(self._nb, bg=BG)
        self._tab_labels  = tk.Frame(self._nb, bg=BG)

        self._nb.add(self._tab_inputs,  text="  INPUTS (52)  ")
        self._nb.add(self._tab_outputs, text="  OUTPUTS (24)  ")
        self._nb.add(self._tab_boxes,   text="  STAGE BOXES  ")
        self._nb.add(self._tab_labels,  text="  LABEL VIEW  ")

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
            (" Clear All",      self._clear_inputs,      RED),
            (" Auto-Name",      self._autonumber_inputs,  YELLOW),
        ]:
            tk.Button(bar, text=txt, command=cmd, font=FTS,
                      bg=BG2, fg=fg, activebackground=BG, activeforeground=fg,
                      relief="flat", bd=0, padx=10, cursor="hand2").pack(
                          side="right", padx=6, pady=6)

        outer, canvas, inner = self._scrollable(tab)

        # column headers
        hrow = tk.Frame(inner, bg=BG2)
        hrow.pack(fill="x", pady=(0,2))
        for txt, w in [(" CH", 4), ("CHANNEL NAME", 22), ("STAGE BOX", 9),
                       ("SOCKET", 7), ("DIR", 4), ("LOCATION", 14), ("NOTE", 18)]:
            tk.Label(hrow, text=txt, font=FTS, bg=BG2, fg=TEXT_DIM,
                     width=w, anchor="w").pack(side="left", padx=4, pady=4)

        self._input_rows = []
        for i in range(NUM_INPUTS):
            self._input_rows.append(self._make_input_row(inner, i))

    def _make_input_row(self, parent, idx):
        d    = self.data.inputs[idx]
        bg   = BG3 if idx % 2 == 0 else BG2
        gcol = BOX_COLORS[idx // 8 % len(BOX_COLORS)]

        frame = tk.Frame(parent, bg=bg)
        frame.pack(fill="x", padx=2, pady=1)

        # Channel number badge
        tk.Label(frame, text=f"{idx+1:02d}", font=FTB,
                 bg=gcol, fg="#1d2021", width=4, anchor="center").pack(
                     side="left", padx=(4,5), pady=3, ipady=2)

        # Name
        name_var = tk.StringVar(value=d["name"])
        tk.Entry(frame, textvariable=name_var, font=FT,
                 bg=BG, fg=TEXT, insertbackground=ACCENT,
                 relief="flat", bd=1, width=22,
                 highlightbackground=BORDER, highlightthickness=1,
                 highlightcolor=ACCENT).pack(side="left", padx=4, pady=3, ipady=3)

        # Stage box selector
        box_var = tk.StringVar(value=d["box"])
        ttk.Combobox(frame, textvariable=box_var, values=BOX_CHOICES,
                     state="readonly", width=7, font=FT).pack(side="left", padx=4, pady=3)

        # Socket selector (populated dynamically)
        socket_var = tk.StringVar(value="none" if d["socket"] == 0 else str(d["socket"]))
        socket_cb  = ttk.Combobox(frame, textvariable=socket_var,
                                  state="readonly", width=5, font=FT)
        socket_cb.pack(side="left", padx=4, pady=3)

        # Direction label
        dir_lbl = tk.Label(frame, text="", font=FTX,
                           bg=bg, fg=TEXT_DIM, width=4, anchor="center")
        dir_lbl.pack(side="left", padx=2, pady=3)

        # Location
        location_var = tk.StringVar(value=d.get("location", ""))
        tk.Entry(frame, textvariable=location_var, font=FTS,
                 bg=BG, fg=PURPLE, insertbackground=PURPLE,
                 relief="flat", bd=1, width=14,
                 highlightbackground=BORDER, highlightthickness=1,
                 highlightcolor=PURPLE).pack(side="left", padx=4, pady=3, ipady=3)

        # Note
        note_var = tk.StringVar(value=d["note"])
        tk.Entry(frame, textvariable=note_var, font=FTS,
                 bg=BG, fg=TEXT_DIM, insertbackground=ACCENT,
                 relief="flat", bd=1, width=18,
                 highlightbackground=BORDER, highlightthickness=1,
                 highlightcolor=ACCENT).pack(side="left", padx=4, pady=3,
                                             ipady=3, fill="x", expand=True)

        row = {"name": name_var, "box": box_var, "socket": socket_var,
               "socket_cb": socket_cb, "dir_lbl": dir_lbl,
               "location": location_var, "note": note_var,
               "frame": frame, "bg": bg}

        def _refresh_sockets(*_, r=row, i=idx):
            if self._building or getattr(self, "_updating", False): return # Added _updating check
            self._fill_input_sockets(r)
            self._sync_input_data(r, i)

        def _on_socket(*_, r=row, i=idx):
            if self._building or getattr(self, "_updating", False): return # Added _updating check
            self._sync_input_data(r, i)
            self._update_dir(r, "IN")

        def _on_name_note(*_, r=row, i=idx):
            if self._building or getattr(self, "_updating", False): return # Added _updating check
            self._sync_input_data(r, i)

        box_var.trace_add("write",      _refresh_sockets)
        socket_var.trace_add("write",   _on_socket)
        name_var.trace_add("write",     _on_name_note)
        location_var.trace_add("write", _on_name_note)
        note_var.trace_add("write",     _on_name_note)

        self._fill_input_sockets(row)
        self._update_dir(row, "IN")
        return row

    def _fill_input_sockets(self, row):
        """Populate socket combo with IN-mode, unassigned sockets for the chosen box.
        The socket this row currently holds is always included so it stays selectable."""
        box = row["box"].get()
        cur = row["socket"].get()
        opts = ["none"]
        if box in self.data.boxes:
            for s in range(1, NUM_SOCKETS + 1):
                if self.data.get_socket_mode(box, s) != "IN":
                    continue
                # Allow: unassigned OR currently held by this row
                if not self.data.is_socket_assigned(box, s) or str(s) == cur:
                    opts.append(str(s))
        row["socket_cb"]["values"] = opts
        row["socket_cb"].set(cur if cur in opts else "none")

    def _sync_input_data(self, row, idx):
        if getattr(self, "_updating", False): return
        self._updating = True
        try:
            sv       = row["socket"].get()
            new_box  = row["box"].get()
            new_sock = 0 if sv == "none" else int(sv)

            # Release the old socket assignment before overwriting
            old_box  = self.data.inputs[idx]["box"]
            old_sock = self.data.inputs[idx]["socket"]
            if old_box != "---" and old_sock > 0:
                self.data.set_socket_assigned(old_box, old_sock, False)

            # Write new values
            self.data.inputs[idx]["name"]     = row["name"].get()
            self.data.inputs[idx]["box"]      = new_box
            self.data.inputs[idx]["socket"]   = new_sock
            self.data.inputs[idx]["location"] = row["location"].get()
            self.data.inputs[idx]["note"]     = row["note"].get()

            # Claim the new socket
            if new_box != "---" and new_sock > 0:
                self.data.set_socket_assigned(new_box, new_sock, True)

            # Refresh other rows' socket lists so they see the freed/taken socket
            self._refresh_all_socket_dropdowns(exclude_input=idx)
        finally:
            self._updating = False

    def _update_dir(self, row, default_mode):
        box = row["box"].get()
        sv  = row["socket"].get()
        lbl = row["dir_lbl"]
        bg  = row["bg"]
        if box == "---" or sv == "none":
            lbl.config(text="", bg=bg)
            return
        mode = self.data.get_socket_mode(box, int(sv))
        lbl.config(text=mode, fg=GREEN if mode == "IN" else OUT_CLR, bg=bg)

    # ═══════════════════════════════════════════
    #  OUTPUTS TAB
    # ═══════════════════════════════════════════
    def _build_outputs_tab(self):
        tab = self._tab_outputs
        bar = tk.Frame(tab, bg=BG2, height=38)
        bar.pack(fill="x")
        tk.Label(bar, text="  OUTPUT PATCH  - 24 Channels",
                 font=FTB, bg=BG2, fg=TEXT_DIM).pack(side="left", padx=12, pady=8)
        tk.Button(bar, text=" Clear All", command=self._clear_outputs, font=FTS,
                  bg=BG2, fg=RED, activebackground=BG, activeforeground=RED,
                  relief="flat", bd=0, padx=10, cursor="hand2").pack(
                      side="right", padx=8, pady=6)

        _, _, inner = self._scrollable(tab)

        hrow = tk.Frame(inner, bg=BG2)
        hrow.pack(fill="x", pady=(0,2))
        for txt, w in [(" OUT", 4), ("OUTPUT NAME", 22), ("TYPE", 12),
                       ("STAGE BOX", 9), ("SOCKET", 7), ("LOCATION", 14), ("NOTE", 18)]:
            tk.Label(hrow, text=txt, font=FTS, bg=BG2, fg=TEXT_DIM,
                     width=w, anchor="w").pack(side="left", padx=4, pady=4)

        self._output_rows = []
        for i in range(NUM_OUTPUTS):
            self._output_rows.append(self._make_output_row(inner, i))

    def _make_output_row(self, parent, idx):
        d  = self.data.outputs[idx]
        bg = BG3 if idx % 2 == 0 else BG2

        frame = tk.Frame(parent, bg=bg)
        frame.pack(fill="x", padx=2, pady=1)

        tk.Label(frame, text=f"{idx+1:02d}", font=FTB,
                 bg=ACCENT2, fg="#1d2021", width=4, anchor="center").pack(
                     side="left", padx=(4,5), pady=3, ipady=2)

        name_var = tk.StringVar(value=d["name"])
        tk.Entry(frame, textvariable=name_var, font=FT,
                 bg=BG, fg=TEXT, insertbackground=ACCENT2,
                 relief="flat", bd=1, width=22,
                 highlightbackground=BORDER, highlightthickness=1,
                 highlightcolor=ACCENT2).pack(side="left", padx=4, pady=3, ipady=3)

        type_var = tk.StringVar(value=d["type"])
        ttk.Combobox(frame, textvariable=type_var, values=OUTPUT_TYPES,
                     state="readonly", width=10, font=FT).pack(side="left", padx=4, pady=3)

        box_var = tk.StringVar(value=d["box"])
        ttk.Combobox(frame, textvariable=box_var, values=BOX_CHOICES,
                     state="readonly", width=7, font=FT).pack(side="left", padx=4, pady=3)

        socket_var = tk.StringVar(value="none" if d["socket"] == 0 else str(d["socket"]))
        socket_cb  = ttk.Combobox(frame, textvariable=socket_var,
                                  state="readonly", width=5, font=FT)
        socket_cb.pack(side="left", padx=4, pady=3)

        location_var = tk.StringVar(value=d.get("location", ""))
        tk.Entry(frame, textvariable=location_var, font=FTS,
                 bg=BG, fg=PURPLE, insertbackground=PURPLE,
                 relief="flat", bd=1, width=14,
                 highlightbackground=BORDER, highlightthickness=1,
                 highlightcolor=PURPLE).pack(side="left", padx=4, pady=3, ipady=3)

        note_var = tk.StringVar(value=d["note"])
        tk.Entry(frame, textvariable=note_var, font=FTS,
                 bg=BG, fg=TEXT_DIM, insertbackground=ACCENT2,
                 relief="flat", bd=1, width=18,
                 highlightbackground=BORDER, highlightthickness=1,
                 highlightcolor=ACCENT2).pack(side="left", padx=4, pady=3,
                                              ipady=3, fill="x", expand=True)

        row = {"name": name_var, "type": type_var, "box": box_var,
               "socket": socket_var, "socket_cb": socket_cb,
               "location": location_var, "note": note_var, "bg": bg}

        def _refresh_sockets(*_, r=row, i=idx):
            if self._building or getattr(self, "_updating", False): return 
            self._fill_output_sockets(r)
            self._sync_output_data(r, i)

        def _on_rest(*_, r=row, i=idx):
            if self._building or getattr(self, "_updating", False): return 
            self._sync_output_data(r, i)

        box_var.trace_add("write",      _refresh_sockets)
        socket_var.trace_add("write",   _on_rest)
        name_var.trace_add("write",     _on_rest)
        type_var.trace_add("write",     _on_rest)
        location_var.trace_add("write", _on_rest)
        note_var.trace_add("write",     _on_rest)

        self._fill_output_sockets(row)
        return row

    def _fill_output_sockets(self, row):
        """Populate socket combo with OUT-mode, unassigned sockets for chosen box.
        The socket this row currently holds is always included so it stays selectable."""
        box = row["box"].get()
        cur = row["socket"].get()
        opts = ["none"]
        if box in self.data.boxes:
            for s in range(1, NUM_SOCKETS + 1):
                if self.data.get_socket_mode(box, s) != "OUT":
                    continue
                # Allow: unassigned OR currently held by this row
                if not self.data.is_socket_assigned(box, s) or str(s) == cur:
                    opts.append(str(s))
        row["socket_cb"]["values"] = opts
        row["socket_cb"].set(cur if cur in opts else "none")

    def _sync_output_data(self, row, idx):
        if getattr(self, "_updating", False): return
        self._updating = True
        try:
            sv       = row["socket"].get()
            new_box  = row["box"].get()
            new_sock = 0 if sv == "none" else int(sv)

            # Release old assignment
            old_box  = self.data.outputs[idx]["box"]
            old_sock = self.data.outputs[idx]["socket"]
            if old_box != "---" and old_sock > 0:
                self.data.set_socket_assigned(old_box, old_sock, False)

            # Write new values
            self.data.outputs[idx]["name"]     = row["name"].get()
            self.data.outputs[idx]["type"]     = row["type"].get()
            self.data.outputs[idx]["box"]      = new_box
            self.data.outputs[idx]["socket"]   = new_sock
            self.data.outputs[idx]["location"] = row["location"].get()
            self.data.outputs[idx]["note"]     = row["note"].get()

            # Claim the new socket
            if new_box != "---" and new_sock > 0:
                self.data.set_socket_assigned(new_box, new_sock, True)

            # Refresh other rows' socket lists
            self._refresh_all_socket_dropdowns(exclude_output=idx)
        finally:
            self._updating = False

    # ═══════════════════════════════════════════
    #  STAGE BOXES TAB
    # ═══════════════════════════════════════════

    def _refresh_all_socket_dropdowns(self, exclude_input=None, exclude_output=None):
        if getattr(self, "_building", True) or getattr(self, "_updating", False):
            return

        self._updating = True  # Block other traces from starting
        try:
            input_rows = getattr(self, "_input_rows", None)
            output_rows = getattr(self, "_output_rows", None)
            
            if input_rows is not None:
                for i, row in enumerate(input_rows):
                    if i != exclude_input:
                        self._fill_input_sockets(row)
                        self._update_dir(row, "IN")
            
            if output_rows is not None:
                for i, row in enumerate(output_rows):
                    if i != exclude_output:
                        self._fill_output_sockets(row)
            
            if hasattr(self, "_patch_labels"):
                self._refresh_box_patch_labels()
        finally:
            self._updating = False  # Always unblock when finished

    def _on_socket_mode_change(self):
        """Called after any flex socket is toggled."""
        # Re-fill socket dropdowns for all channels
        for row in self._input_rows:
            self._fill_input_sockets(row)
            self._update_dir(row, "IN")
        for row in self._output_rows:
            self._fill_output_sockets(row)
        self._refresh_box_patch_labels()

    def _refresh_box_patch_labels(self):
        """Update the small patch-info labels on the Stage Boxes tab."""
        # Build map (box, socket) -> display string
        lookup = {}
        for i, ch in enumerate(self.data.inputs):
            if ch["box"] != "---" and ch["socket"] > 0:
                lbl = f"I{i+1:02d} {ch['name']}"
                lookup[(ch["box"], ch["socket"])] = (lbl, ACCENT)
        for i, ch in enumerate(self.data.outputs):
            if ch["box"] != "---" and ch["socket"] > 0:
                lbl = f"O{i+1:02d} {ch['name']}"
                lookup[(ch["box"], ch["socket"])] = (lbl, ACCENT2)

        for (box, snum), widget in self._patch_labels.items():
            if (box, snum) in lookup:
                txt, clr = lookup[(box, snum)]
                widget.config(text=txt, fg=clr)
            else:
                widget.config(text="", fg=TEXT_DIM)

    # ═══════════════════════════════════════════
    #  LABEL VIEW TAB
    # ═══════════════════════════════════════════
    def _build_labels_tab(self):
        tab = self._tab_labels
        bar = tk.Frame(tab, bg=BG2, height=38)
        bar.pack(fill="x")
        tk.Label(bar, text="  LABEL OVERVIEW",
                 font=FTB, bg=BG2, fg=TEXT_DIM).pack(side="left", padx=12, pady=8)
        tk.Button(bar, text="-> Refresh", command=self._refresh_labels, font=FTS,
                  bg=BG2, fg=GREEN, activebackground=BG, activeforeground=GREEN,
                  relief="flat", bd=0, padx=10, cursor="hand2").pack(
                      side="right", padx=8, pady=6)

        body = tk.Frame(tab, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=8)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=0, minsize=14)
        body.columnconfigure(2, weight=2)
        body.rowconfigure(0, weight=1)

        # Stage box column
        sb_frame = tk.Frame(body, bg=BG)
        sb_frame.grid(row=0, column=0, sticky="nsew")
        tk.Label(sb_frame, text="STAGE BOX LABELS",
                 font=FTH, bg=BG, fg=ACCENT).pack(anchor="w", pady=(0,6))
        sb_c, self._sb_canvas = self._scrollframe(sb_frame)
        self._sb_inner = sb_c

        tk.Frame(body, bg=BORDER, width=2).grid(row=0, column=1, sticky="ns", padx=6)

        # Output column
        out_frame = tk.Frame(body, bg=BG)
        out_frame.grid(row=0, column=2, sticky="nsew")
        tk.Label(out_frame, text="OUTPUT LABELS",
                 font=FTH, bg=BG, fg=ACCENT2).pack(anchor="w", pady=(0,6))
        out_c, self._out_canvas = self._scrollframe(out_frame)
        self._out_inner = out_c

    def _refresh_labels(self):
        # ── Stage boxes ──
        for w in self._sb_inner.winfo_children():
            w.destroy()

        patch_map = {}
        for i, ch in enumerate(self.data.inputs):
            if ch["box"] != "---" and ch["socket"] > 0:
                patch_map[(ch["box"], ch["socket"])] = (i+1, ch["name"], "IN")
        for i, ch in enumerate(self.data.outputs):
            if ch["box"] != "---" and ch["socket"] > 0:
                patch_map[(ch["box"], ch["socket"])] = (i+1, ch["name"], "OUT")

        for bi, box_name in enumerate(STAGE_BOX_NAMES):
            clr   = BOX_COLORS[bi % len(BOX_COLORS)]
            bdata = self.data.boxes[box_name]
            label = bdata.get("name", box_name)

            hdr = tk.Frame(self._sb_inner, bg=clr)
            hdr.pack(fill="x", pady=(10,2), padx=2)
            tk.Label(hdr, text=f"  {label}  ({box_name})",
                     font=FTB, bg=clr, fg="#1d2021").pack(side="left", padx=6, pady=4)

            grid_f = tk.Frame(self._sb_inner, bg=BG2)
            grid_f.pack(fill="x", padx=2, pady=(0,2))

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
                tk.Label(cell, text=f"S{snum:02d}", font=FTX,
                         bg=badge_clr, fg="#1d2021", width=4).pack(side="left", ipady=3)
                if is_flex:
                    tk.Label(cell, text=mode, font=FTX,
                             bg=BG3, fg=badge_clr).pack(side="left", padx=2)

                key = (box_name, snum)
                if key in patch_map:
                    cnum, cname, kind = patch_map[key]
                    tag_clr = ACCENT if kind == "IN" else ACCENT2
                    prefix  = f"I{cnum:02d}" if kind == "IN" else f"O{cnum:02d}"
                    tk.Label(cell, text=prefix, font=FTX,
                             bg=BG3, fg=tag_clr).pack(side="left", padx=(4,1))
                    tk.Label(cell, text=cname or "-", font=FT,
                             bg=BG3, fg=TEXT, anchor="w").pack(
                                 side="left", padx=2, pady=3, fill="x", expand=True)
                    # Show location if set
                    src_list = self.data.inputs if kind == "IN" else self.data.outputs
                    loc = src_list[cnum - 1].get("location", "")
                    if loc:
                        tk.Label(cell, text=f"{loc}", font=FTX,
                                 bg=BG3, fg=PURPLE, anchor="w").pack(side="left", padx=(0,4))
                else:
                    tk.Label(cell, text="-", font=FTX,
                             bg=BG3, fg=TEXT_DIM, anchor="w").pack(
                                 side="left", padx=6, pady=3, fill="x", expand=True)

        self._sb_canvas.update_idletasks()
        self._sb_canvas.configure(scrollregion=self._sb_canvas.bbox("all"))

        # ── Output labels ──
        for w in self._out_inner.winfo_children():
            w.destroy()

        for i, out in enumerate(self.data.outputs):
            bg = BG3 if i % 2 == 0 else BG2
            f  = tk.Frame(self._out_inner, bg=bg)
            f.pack(fill="x", padx=2, pady=1)
            tk.Label(f, text=f"{i+1:02d}", font=FTB,
                     bg=ACCENT2, fg="#1d2021", width=4).pack(side="left", padx=(4,5), pady=4, ipady=1)
            tk.Label(f, text=out["name"] or "-", font=FT,
                     bg=bg, fg=TEXT, anchor="w", width=16).pack(side="left", padx=4)
            tk.Label(f, text=out["type"], font=FTS,
                     bg=bg, fg=TEXT_DIM, anchor="w", width=10).pack(side="left", padx=2)
            if out["box"] != "---" and out["socket"] > 0:
                tk.Label(f, text=f"-> {out['box']} S{out['socket']:02d}", font=FTS,
                         bg=bg, fg=ACCENT2, anchor="w").pack(side="left", padx=6)
            loc = out.get("location", "")
            if loc:
                tk.Label(f, text=f" {loc}", font=FTS,
                         bg=bg, fg=PURPLE, anchor="w").pack(side="left", padx=6)

        self._out_canvas.update_idletasks()
        self._out_canvas.configure(scrollregion=self._out_canvas.bbox("all"))

    # ═══════════════════════════════════════════
    #  Shared scrollable helpers
    # ═══════════════════════════════════════════
    def _scrollable(self, parent, horizontal=False):
        """Return (outer_frame, canvas, inner_frame) with scroll bars."""
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
        wid   = canvas.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(wid, width=e.width))
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        return outer, canvas, inner

    def _scrollframe(self, parent):
        """Return (inner_frame, canvas) for a simple scrollable section."""
        canvas = tk.Canvas(parent, bg=BG, bd=0, highlightthickness=0)
        vs     = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vs.set)
        vs.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner  = tk.Frame(canvas, bg=BG)
        wid    = canvas.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(wid, width=e.width))
        return inner, canvas

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
            self.data.rebuild_assigned_from_data()
             # Recompute all isAssigned flags from current data before rebuilding dropdowns
            self.data.rebuild_assigned_from_data()
            for i, row in enumerate(self._input_rows):
                d = self.data.inputs[i]
                row["name"].set(d["name"])
                row["box"].set(d["box"])
                row["location"].set(d.get("location", ""))
                row["note"].set(d["note"])
                self._fill_input_sockets(row)
                row["socket"].set("none" if d["socket"] == 0 else str(d["socket"]))
                self._update_dir(row, "IN")
            for i, row in enumerate(self._output_rows):
                d = self.data.outputs[i]
                row["name"].set(d["name"])
                row["type"].set(d["type"])
                row["box"].set(d["box"])
                row["location"].set(d.get("location", ""))
                row["note"].set(d["note"])
                self._fill_output_sockets(row)
                row["socket"].set("none" if d["socket"] == 0 else str(d["socket"]))
            self._show_var.set(self.data.show_name)
        finally:
            self._updating = False
       

    # ═══════════════════════════════════════════
    #  Clear / auto-name
    # ═══════════════════════════════════════════
    def _clear_inputs(self):
        if messagebox.askyesno("Clear Inputs", "Clear all 52 input channels?"):
            for i in range(NUM_INPUTS):
                self.data.inputs[i] = {"name": "", "box": "---", "socket": 0, "location": "", "note": ""}
            self.data.rebuild_assigned_from_data()
            self._refresh_all()

    def _clear_outputs(self):
        if messagebox.askyesno("Clear Outputs", "Clear all 24 output channels?"):
            for i in range(NUM_OUTPUTS):
                self.data.outputs[i] = {"name": "", "type": "---",
                                         "box": "---", "socket": 0, "location": "", "note": ""}
            self.data.rebuild_assigned_from_data()
            self._refresh_all()

    def _autonumber_inputs(self):
        for i, row in enumerate(self._input_rows):
            if not row["name"].get():
                row["name"].set(f"Input {i+1:02d}")

    # ═══════════════════════════════════════════
    #  File I/O
    # ═══════════════════════════════════════════
    def _save(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Patch File", "*.json"), ("All Files", "*.*")],
            title="Save Patch File",
            initialfile=f"{self.data.show_name.replace(' ','_')}.json")
        if not path:
            return
        with open(path, "w") as f:
            json.dump(self.data.to_dict(), f, indent=2)
        messagebox.showinfo("Saved", f"Patch saved:\n{path}")

    def _load(self):
        path = filedialog.askopenfilename(
            filetypes=[("Patch File", "*.json"), ("All Files", "*.*")],
            title="Load Patch File")
        if not path:
            return
        with open(path) as f:
            d = json.load(f)
        self.data.from_dict(d)
        self._refresh_all()
        messagebox.showinfo("Loaded", f"Patch loaded:\n{path}")

    def _export_txt(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text File", "*.txt"), ("All Files", "*.*")],
            title="Export Patch List",
            initialfile=f"{self.data.show_name.replace(' ','_')}_patch.txt")
        if not path:
            return
        w = 88
        lines = [f"PATCH LIST - {self.data.show_name}", "=" * w, ""]

        # ── Stage box socket config ──────────────────────────────────────────
        lines += ["STAGE BOX SOCKET CONFIG", "-" * w]
        for bn in STAGE_BOX_NAMES:
            bd   = self.data.boxes[bn]
            line = f"  {bd['name']:10s} ({bn}):  "
            for si in range(NUM_SOCKETS):
                mode = bd["socket_mode"][si]
                line += f"S{si+1:02d}:{mode}  "
            lines.append(line)

        # ── Inputs ───────────────────────────────────────────────────────────
        lines += ["", "INPUTS", "-" * w,
                  f"{'CH':<5} {'NAME':<24} {'BOX':<8} {'SOCKET':<7} {'DIR':<5} {'LOCATION':<16} {'NOTE'}"]
        for i, ch in enumerate(self.data.inputs):
            sstr = f"S{ch['socket']:02d}" if ch["socket"] > 0 else "-"
            mstr = self.data.get_socket_mode(ch["box"], ch["socket"]) \
                   if ch["box"] != "---" and ch["socket"] > 0 else ""
            loc  = ch.get("location", "")
            lines.append(
                f"{i+1:<5} {ch['name']:<24} {ch['box']:<8} {sstr:<7} {mstr:<5} {loc:<16} {ch['note']}")

        # ── Outputs ──────────────────────────────────────────────────────────
        lines += ["", "OUTPUTS", "-" * w,
                  f"{'OUT':<5} {'NAME':<24} {'TYPE':<14} {'BOX':<8} {'SOCKET':<7} {'LOCATION':<16} {'NOTE'}"]
        for i, out in enumerate(self.data.outputs):
            sstr = f"S{out['socket']:02d}" if out["socket"] > 0 else "-"
            loc  = out.get("location", "")
            lines.append(
                f"{i+1:<5} {out['name']:<24} {out['type']:<14} {out['box']:<8} {sstr:<7} {loc:<16} {out['note']}")

        # ── Stage Box Labels ─────────────────────────────────────────────────
        lines += ["", "", "═" * w,
                  "STAGE BOX LABELS", "═" * w]

        patch_map = {}
        for i, ch in enumerate(self.data.inputs):
            if ch["box"] != "---" and ch["socket"] > 0:
                patch_map[(ch["box"], ch["socket"])] = (i+1, ch["name"], ch.get("location",""), "IN")
        for i, ch in enumerate(self.data.outputs):
            if ch["box"] != "---" and ch["socket"] > 0:
                patch_map[(ch["box"], ch["socket"])] = (i+1, ch["name"], ch.get("location",""), "OUT")

        for bn in STAGE_BOX_NAMES:
            bd    = self.data.boxes[bn]
            label = bd.get("name", bn)
            lines += ["", f"  ┌─── {label} ({bn}) {'─'*(w-12-len(label)-len(bn))}┐"]
            for si in range(NUM_SOCKETS):
                snum = si + 1
                mode = bd["socket_mode"][si]
                key  = (bn, snum)
                if key in patch_map:
                    cnum, cname, cloc, kind = patch_map[key]
                    prefix = f"I{cnum:02d}" if kind == "IN" else f"O{cnum:02d}"
                    loc_str = f"  [{cloc}]" if cloc else ""
                    lines.append(f"  │  S{snum:02d} [{mode:3s}]  {prefix} {cname:<22}{loc_str}")
                else:
                    lines.append(f"  │  S{snum:02d} [{mode:3s}]  -")
            lines.append(f"  └{'─'*(w-4)}┘")

        # ── Output Labels ────────────────────────────────────────────────────
        lines += ["", "", "═" * w,
                  "OUTPUT LABELS", "═" * w, ""]
        lines.append(f"  {'OUT':<5} {'NAME':<24} {'TYPE':<14} {'BOX':<10} {'SOCKET':<8} {'LOCATION'}")
        lines.append("  " + "-" * (w - 2))
        for i, out in enumerate(self.data.outputs):
            if not out["name"] and out["box"] == "---":
                continue
            sstr = f"S{out['socket']:02d}" if out["socket"] > 0 else "-"
            loc  = out.get("location", "")
            lines.append(
                f"  {i+1:<5} {out['name']:<24} {out['type']:<14} {out['box']:<10} {sstr:<8} {loc}")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        messagebox.showinfo("Exported", f"Patch list exported:\n{path}")

    # ── Stage Boxes Tab ──────────────────────────
    def _build_boxes_tab(self):
        self._patch_labels = {}
        tab = self._tab_boxes
        bar = tk.Frame(tab, bg=BG2, height=38)
        bar.pack(fill="x")
        tk.Label(bar,
                 text="  STAGE BOX CONFIG  -  Sockets 1-8: fixed IN  |  Sockets 9-12: toggle IN / OUT",
                 font=FTB, bg=BG2, fg=TEXT_DIM).pack(side="left", padx=12, pady=8)

        _, canvas, inner = self._scrollable(tab, horizontal=True)

        COLS = 4
        for bi, box_name in enumerate(STAGE_BOX_NAMES):
            col       = bi % COLS
            row_start = (bi // COLS) * 15
            clr       = BOX_COLORS[bi % len(BOX_COLORS)]
            inner.columnconfigure(col, weight=1)

            # Editable box header
            hdr = tk.Frame(inner, bg=clr)
            hdr.grid(row=row_start, column=col, padx=8, pady=(14,2), sticky="ew")
            bname_var = tk.StringVar(value=self.data.boxes[box_name]["name"])
            tk.Entry(hdr, textvariable=bname_var, font=FTB,
                     bg=clr, fg="#1d2021", insertbackground="#1d2021",
                     relief="flat", bd=0, width=10).pack(side="left", padx=8, pady=5)
            tk.Label(hdr, text=f"({box_name})", font=FTX,
                     bg=clr, fg="#1d2021").pack(side="left")
            
            def _save_name(*_, bn=box_name, v=bname_var):
                self.data.boxes[bn]["name"] = v.get()
            bname_var.trace_add("write", _save_name)

            # Socket rows
            for si in range(NUM_SOCKETS):
                snum    = si + 1
                is_flex = snum >= FLEX_START
                mode    = self.data.boxes[box_name]["socket_mode"][si]
                sf_bg   = BG3 if si % 2 == 0 else BG2

                sf = tk.Frame(inner, bg=sf_bg)
                sf.grid(row=row_start + 1 + si, column=col,
                        padx=8, pady=1, sticky="ew")

                badge_clr = GREEN if mode == "IN" else OUT_CLR
                sn_lbl = tk.Label(sf, text=f"S{snum:02d}", font=FTX,
                                  bg=badge_clr, fg="#1d2021", width=4)
                sn_lbl.pack(side="left", ipady=3)

                if is_flex:
                    mode_var = tk.StringVar(value=mode)
                    btn = tk.Button(sf, text=mode, font=FTX, width=4,
                                   bg=badge_clr, fg="#1d2021",
                                   relief="flat", bd=0, cursor="hand2")

                    def _make_toggle(bn=box_name, sn=snum, mv=mode_var,
                                     b=btn, sl=sn_lbl):
                        def toggle(_=None):
                            new     = "OUT" if mv.get() == "IN" else "IN"
                            nc      = GREEN if new == "IN" else OUT_CLR
                            mv.set(new)
                            b.config(text=new, bg=nc, fg="#1d2021")
                            sl.config(bg=nc, fg="#1d2021")
                            self.data.set_socket_mode(bn, sn, new)
                            self._on_socket_mode_change()
                        return toggle

                    btn.config(command=_make_toggle())
                    btn.pack(side="left", padx=6, pady=3, ipady=1)
                else:
                    tk.Label(sf, text="IN", font=FTX,
                             bg=sf_bg, fg=GREEN).pack(side="left", padx=8)

                pl = tk.Label(sf, text="", font=FTX,
                              bg=sf_bg, fg=TEXT_DIM, anchor="w")
                pl.pack(side="left", padx=4, fill="x", expand=True)
                self._patch_labels[(box_name, snum)] = pl

        self.after(200, self._refresh_box_patch_labels)


# ─────────────────────────────────────────────
if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        # This will catch errors that might be closing the window instantly
        print(f"Error starting application: {e}")
