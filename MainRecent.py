"""
Stage Box & Audio Patch Manager  (Multi-Band Pro Edition)
------------------------------------------------------
Refactored to match the professional UI specification.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import string
import sys
import socket
import threading
import queue
import time
import hashlib

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
#  Theme (Modern Deep Slate UI Palette)
# ─────────────────────────────────────────────
BG         = "#09090b"  # Deep layout background (Zinc 950)
BG2        = "#18181b"  # Sidebar and main panel background (Zinc 900)
BG3        = "#27272a"  # Input controls and alternating row fields (Zinc 800)
BORDER     = "#3f3f46"  # Clean borders (Zinc 700)

TEXT       = "#fafafa"  # Pure crisp light text for legibility (Zinc 50)
TEXT_DIM   = "#a1a1aa"  # Muted secondary text elements (Zinc 400)
DARK_TXT   = "#09090b"  # Deep contrast text inside active channel badges

ACCENT     = "#06b6d4"  # Modern Cyan
ACCENT2    = "#6366f1"  # Modern Indigo
PURPLE     = "#a855f7"  # Electric Purple

GREEN      = "#10b981"  # Emerald Green badge
YELLOW     = "#eab308"  # Amber Warning Yellow
RED        = "#ef4444"  # Vibrant alert Red
OUT_CLR    = "#f97316"  # Bright Orange badge

FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "Helvetica"

FT   = (FONT_FAMILY, 10)
FTS  = (FONT_FAMILY, 9)
FTX  = (FONT_FAMILY, 8)
FTB  = (FONT_FAMILY, 10, "bold")
FTM  = (FONT_FAMILY, 11, "bold")
FTH  = (FONT_FAMILY, 13, "bold")
FTTL = (FONT_FAMILY, 15, "bold")
FTXL = (FONT_FAMILY, 20, "bold")

BOX_COLORS = ["#06b6d4", "#10b981", "#f97316", "#ef4444", "#a855f7", "#6366f1"]

# ─────────────────────────────────────────────
#  Live Sync Architecture Constants
# ─────────────────────────────────────────────
SYNC_DEFAULT_PORT = 51515
SYNC_POLL_MS      = 800     

# ─────────────────────────────────────────────
#  Modern Canvas Scrolling Engine
# ─────────────────────────────────────────────
def attach_mouse_scroll(container, canvas):
    def _on_mousewheel(event):
        if getattr(event, 'num', 0) == 4:
            canvas.yview_scroll(-1, "units")
            return
        elif getattr(event, 'num', 0) == 5:
            canvas.yview_scroll(1, "units")
            return
        delta = getattr(event, 'delta', 0)
        if delta != 0:
            if sys.platform == 'darwin':
                canvas.yview_scroll(int(-1 * delta), "units")
            else:
                canvas.yview_scroll(int(-1 * (delta / 120)), "units")

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
    outer = tk.Frame(parent, bg=BG)
    outer.pack(fill="both", expand=True)
    canvas = tk.Canvas(outer, bg=BG, bd=0, highlightthickness=0)
    vs = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vs.set)
    if horizontal:
        hs = ttk.Scrollbar(outer, orient="horizontal", command=canvas.xview)
        canvas.configure(xscrollcommand=hs.set)
        hs.pack(side="bottom", fill="x")
    vs.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg=BG)
    wid = canvas.create_window((0, 0), window=inner, anchor="nw")
    
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(wid, width=e.width))

    attach_mouse_scroll(outer, canvas)
    return outer, canvas, inner


def make_scrollframe(parent):
    canvas = tk.Canvas(parent, bg=BG2, bd=0, highlightthickness=0)
    vs = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vs.set)
    vs.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg=BG2)
    wid = canvas.create_window((0, 0), window=inner, anchor="nw")
    
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(wid, width=e.width))
    
    attach_mouse_scroll(parent, canvas)
    return inner, canvas

# ─────────────────────────────────────────────
#  Application Structural Components
# ─────────────────────────────────────────────
def styled_button(parent, text, command, fg=TEXT, bg=BG3, hover_bg=BORDER, font=None, padx=14, pady=6, padding=None):
    font = font or FTB
    btn = tk.Button(parent, text=text, command=command, font=font,
                    bg=bg, fg=fg, activebackground=hover_bg or bg, activeforeground=fg,
                    relief="flat", bd=0, padx=padx, pady=pady, cursor="hand2", highlightthickness=0)
    btn.bind("<Enter>", lambda _e: btn.configure(bg=hover_bg))
    btn.bind("<Leave>", lambda _e: btn.configure(bg=bg))
    return btn


def make_card(parent, title=None, subtitle=None, accent=ACCENT):
    outer = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
    if accent:
        tk.Frame(outer, bg=accent, height=2).pack(fill="x", side="top")
    if title:
        head = tk.Frame(outer, bg=BG2)
        head.pack(fill="x", padx=16, pady=(12, 4 if subtitle else 12))
        tk.Label(head, text=title, font=FTH, bg=BG2, fg=TEXT).pack(anchor="w")
        if subtitle:
            tk.Label(outer, text=subtitle, font=FTS, bg=BG2, fg=TEXT_DIM, justify="left").pack(anchor="w", padx=16, pady=(0, 12))
    return outer


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()

# ─────────────────────────────────────────────
#  Data Architecture Model
# ─────────────────────────────────────────────
def _default_box(name):
    return {
        "name":            f"Stage Box {name}",
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

        self.inputs  = [{"name": "", "box": "---", "socket": 0, "note": "", "location": ""} for _ in range(NUM_INPUTS)]
        self.outputs = [{"name": "", "type": "---", "box": "---", "socket": 0, "note": "", "location": ""} for _ in range(NUM_OUTPUTS)]

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
            raw.setdefault("name", f"Stage Box {letter}")
            band.box_order.append(letter)
            band.boxes[letter] = raw

        raw_inputs  = d.get("inputs",  band.inputs)
        raw_outputs = d.get("outputs", band.outputs)
        for ch in raw_inputs: ch.setdefault("location", "")
        for ch in raw_outputs: ch.setdefault("location", "")
        band.inputs  = raw_inputs
        band.outputs = raw_outputs
        band.rebuild_assigned_from_data()
        return band


class ShowData:
    def __init__(self):
        self.show_name = "Arena Tour 2026"
        self.bands = [BandData(band_name="Band 1"), BandData(band_name="Band 2")]

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


def build_band_report_lines(band, width=88):
    lines = [f"BAND: {band.band_name}", "=" * width, ""]
    lines += ["STAGE BOX SOCKET CONFIG", "-" * width]
    for bn in band.box_order:
        bd   = band.boxes[bn]
        line = f"  {bd['name']:14s} ({bn}):  "
        for si in range(NUM_SOCKETS):
            mode = bd["socket_mode"][si]
            line += f"S{si+1:02d}:{mode}  "
        lines.append(line)
    return lines


# ─────────────────────────────────────────────
#  Global Network Synchronizer Engine
# ─────────────────────────────────────────────
class SyncManager:
    def __init__(self, app):
        self.app = app
        self.mode = "off"          
        self.role_status = "Idle"
        self.port = SYNC_DEFAULT_PORT
        self.host_ip = ""
        self.server_sock = None
        self.client_sock = None
        self.client_conns = {}     
        self.incoming = queue.Queue()
        self.version = 0
        self.last_sent_hash = None
        self.last_applied_hash = None
        self._stop_flag = threading.Event()
        self._poll_job = None

    def start_host(self, port):
        self.stop()
        self._stop_flag.clear()
        self.port = port
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("0.0.0.0", port))
            srv.listen(8)
        except OSError as e:
            self.role_status = f"Could not host: {e}"
            return False
        self.server_sock = srv
        self.mode = "host"
        self.role_status = f"Hosting on port {port}"
        threading.Thread(target=self._accept_loop, daemon=True).start()
        self.last_sent_hash = None     
        self._start_poll()
        return True

    def start_client(self, host_ip, port):
        self.stop()
        self._stop_flag.clear()
        self.host_ip, self.port = host_ip, port
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host_ip, port))
            sock.settimeout(None)
        except OSError as e:
            self.role_status = f"Fail: {e}"
            return False
        self.client_sock = sock
        self.mode = "client"
        self.role_status = f"Connected to {host_ip}"
        threading.Thread(target=self._recv_loop, args=(sock,), daemon=True).start()
        self._start_poll()
        return True

    def stop(self):
        self._stop_flag.set()
        self.mode = "off"
        self.role_status = "Idle"
        if self.server_sock:
            try: self.server_sock.close()
            except OSError: pass
            self.server_sock = None
        for sock in list(self.client_conns.values()):
            try: sock.close()
            except OSError: pass
        self.client_conns.clear()
        if self.client_sock:
            try: self.client_sock.close()
            except OSError: pass
            self.client_sock = None
        if self._poll_job:
            try: self.app.after_cancel(self._poll_job)
            except Exception: pass
            self._poll_job = None

    def _accept_loop(self):
        while not self._stop_flag.is_set():
            try: conn, addr = self.server_sock.accept()
            except OSError: break
            self.client_conns[addr] = conn
            threading.Thread(target=self._recv_loop, args=(conn,), daemon=True).start()
            self._send_to(conn, self._snapshot_payload())

    def _broadcast(self, payload, exclude=None):
        raw = self._encode(payload)
        dead = []
        for addr, sock in self.client_conns.items():
            if sock is exclude: continue
            try: sock.sendall(raw)
            except OSError: dead.append(addr)
        for addr in dead: self.client_conns.pop(addr, None)

    @staticmethod
    def _encode(payload):
        raw = json.dumps(payload).encode("utf-8")
        return len(raw).to_bytes(4, "big") + raw

    def _send_to(self, sock, payload):
        try: sock.sendall(self._encode(payload))
        except OSError: pass

    @staticmethod
    def _recv_exact(sock, n):
        data = b""
        while len(data) < n:
            try: chunk = sock.recv(n - len(data))
            except OSError: return None
            if not chunk: return None
            data += chunk
        return data

    def _recv_loop(self, sock):
        try:
            while not self._stop_flag.is_set():
                header = self._recv_exact(sock, 4)
                if header is None: break
                length = int.from_bytes(header, "big")
                body = self._recv_exact(sock, length)
                if body is None: break
                try: payload = json.loads(body.decode("utf-8"))
                except json.JSONDecodeError: continue
                self.incoming.put((sock, payload))
        finally:
            if self.mode == "host":
                for addr, s in list(self.client_conns.items()):
                    if s is sock: self.client_conns.pop(addr, None)
            elif self.mode == "client" and sock is self.client_sock:
                self.role_status = "Disconnected"

    def _snapshot_payload(self):
        self.version += 1
        return {"v": self.version, "ts": time.time(), "data": self.app.show.to_dict()}

    def _start_poll(self):
        self._poll()

    def _poll(self):
        if self.mode == "off": return
        applied = False
        while True:
            try: sock, payload = self.incoming.get_nowait()
            except queue.Empty: break
            applied = self._handle_incoming(sock, payload) or applied
        if applied:
            self.app._apply_remote_show_update()
        try:
            current = json.dumps(self.app.show.to_dict(), sort_keys=True)
            h = hashlib.sha1(current.encode("utf-8")).hexdigest()
        except Exception: h = None

        if h is not None and h != self.last_sent_hash and h != self.last_applied_hash:
            self.last_sent_hash = h
            payload = self._snapshot_payload()
            if self.mode == "host" and self.client_conns: self._broadcast(payload)
            elif self.mode == "client" and self.client_sock: self._send_to(self.client_sock, payload)

        self._poll_job = self.app.after(SYNC_POLL_MS, self._poll)

    def _handle_incoming(self, sock, payload):
        data = payload.get("data")
        v = payload.get("v", 0)
        if data is None: return False
        applied = False
        if self.mode == "host":
            self._broadcast(payload, exclude=sock)
            if v >= self.version:
                self.version = v
                self.app.show.from_dict(data)
                applied = True
        elif self.mode == "client":
            if v >= self.version:
                self.version = v
                self.app.show.from_dict(data)
                applied = True
        if applied:
            current = json.dumps(self.app.show.to_dict(), sort_keys=True)
            self.last_applied_hash = hashlib.sha1(current.encode("utf-8")).hexdigest()
            self.last_sent_hash = self.last_applied_hash
        return applied


# ─────────────────────────────────────────────
#  Global/All Labels Dashboard Overview
# ─────────────────────────────────────────────
class AllLabelsPanel(tk.Frame):
    def __init__(self, master, app, show: ShowData):
        super().__init__(master, bg=BG)
        self.app = app
        self.show = show
        self._cache = {"structural_key": None, "widgets": {}}
        self._build()

    def _build(self):
        bar = tk.Frame(self, bg=BG2, height=50)
        bar.pack(fill="x")
        tk.Label(bar, text="🌎  ALL BANDS OVERVIEW", font=FTTL, bg=BG2, fg=TEXT).pack(side="left", padx=16, pady=10)
        styled_button(bar, "↻ Refresh Overview", lambda: self.refresh_all_labels(force=True), fg=GREEN, bg=BG3).pack(side="right", padx=16, pady=8)

        self._inner, self._canvas = make_scrollframe(self)

    def refresh_all_labels(self, force=False):
        """Mutates existing text values seamlessly to avoid artifacts and screen flicker."""
        if not self.show.bands:
            for w in self._inner.winfo_children(): w.destroy()
            self._cache = {"structural_key": "empty", "widgets": {}}
            tk.Label(self._inner, text="No active configuration sheets detected.", font=FTH, bg=BG2, fg=TEXT_DIM).pack(pady=40)
            return

        # Generate structural fingerprint (Bands configuration schema tracker)
        struct_fingerprint = "|".join([f"{b.band_name}:{len(b.box_order)}" for b in self.show.bands])

        if self._cache.get("structural_key") != struct_fingerprint or force:
            for w in self._inner.winfo_children(): w.destroy()
            self._cache = {"structural_key": struct_fingerprint, "widgets": {}}

            for bi, band in enumerate(self.show.bands):
                box_frame = tk.Frame(self._inner, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
                box_frame.pack(fill="x", padx=16, pady=12)

                hdr = tk.Frame(box_frame, bg=BG3)
                hdr.pack(fill="x")
                
                band_lbl = tk.Label(hdr, text=f"🎸  {band.band_name.upper()}", font=FTB, bg=BG3, fg=BOX_COLORS[bi % len(BOX_COLORS)])
                band_lbl.pack(side="left", padx=12, pady=8)
                self._cache["widgets"][(bi, "band_name")] = band_lbl

                body = tk.Frame(box_frame, bg=BG2, padx=12, pady=12)
                body.pack(fill="x")

                for box_name in band.box_order:
                    f = tk.Frame(body, bg=BG3, highlightthickness=1, highlightbackground=BORDER)
                    f.pack(fill="x", pady=4)
                    
                    b_head = tk.Frame(f, bg=BORDER)
                    b_head.pack(fill="x")
                    
                    box_lbl = tk.Label(b_head, text=f"Stage Box ({box_name})", font=FTB, bg=BORDER, fg=TEXT)
                    box_lbl.pack(side="left", padx=8, pady=4)
                    self._cache["widgets"][(bi, box_name, "box_title")] = box_lbl

                    grid = tk.Frame(f, bg=BG3, padx=6, pady=6)
                    grid.pack(fill="x")

                    for si in range(NUM_SOCKETS):
                        snum = si + 1
                        col = si % 4
                        row_g = si // 4
                        grid.columnconfigure(col, weight=1)

                        cell = tk.Frame(grid, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
                        cell.grid(row=row_g, column=col, padx=4, pady=4, sticky="ew")

                        badge = tk.Label(cell, text=f"S{snum:02d}", font=FTX, bg=BG2, fg=DARK_TXT, width=4)
                        badge.pack(side="left")

                        txt_lbl = tk.Label(cell, text="-", font=FTS, bg=BG2, fg=TEXT, anchor="w")
                        txt_lbl.pack(side="left", padx=6, fill="x", expand=True)

                        self._cache["widgets"][(bi, box_name, snum)] = (badge, txt_lbl)

        # Seamless data mutation pass
        for bi, band in enumerate(self.show.bands):
            if (bi, "band_name") in self._cache["widgets"]:
                self._cache["widgets"][(bi, "band_name")].config(text=f"🎸  {band.band_name.upper()}")

            patch_map = {}
            for i, ch in enumerate(band.inputs):
                if ch["box"] != "---" and ch["socket"] > 0: 
                    patch_map[(ch["box"], ch["socket"])] = (i + 1, ch["name"], "IN")
            for i, ch in enumerate(band.outputs):
                if ch["box"] != "---" and ch["socket"] > 0: 
                    patch_map[(ch["box"], ch["socket"])] = (i + 1, ch["name"], "OUT")

            for box_name in band.box_order:
                bd = band.boxes[box_name]
                lbl_txt = bd.get("name", f"Stage Box {box_name}")
                if (bi, box_name, "box_title") in self._cache["widgets"]:
                    self._cache["widgets"][(bi, box_name, "box_title")].config(text=f"{lbl_txt} ({box_name})")

                for si in range(NUM_SOCKETS):
                    snum = si + 1
                    mode = bd["socket_mode"][si]
                    key = (box_name, snum)

                    if (bi, box_name, snum) in self._cache["widgets"]:
                        badge, txt_lbl = self._cache["widgets"][(bi, box_name, snum)]
                        b_clr = GREEN if mode == "IN" else OUT_CLR
                        badge.config(bg=b_clr)

                        if key in patch_map:
                            cnum, cname, kind = patch_map[key]
                            pfx = f"I{cnum:02d}" if kind == "IN" else f"O{cnum:02d}"
                            txt_lbl.config(text=f"{pfx}: {cname or '-'}", fg=TEXT)
                        else:
                            txt_lbl.config(text="-", fg=TEXT_DIM)

        self._canvas.update_idletasks()
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))


# ─────────────────────────────────────────────
#  Central Workspace Band Configuration Panel
# ─────────────────────────────────────────────
class BandPanel(tk.Frame):
    def __init__(self, master, app, band: BandData):
        super().__init__(master, bg=BG)
        self.app = app
        self.band = band
        self._building = True
        self._updating = False
        self._search_query = ""

        self._build()
        self._building = False
        self._refresh_all()

    def _build(self):
        # Header Controls
        hdr_bar = tk.Frame(self, bg=BG, height=50)
        hdr_bar.pack(fill="x", pady=(0, 10))
        
        lbl_wrap = tk.Frame(hdr_bar, bg=BG)
        lbl_wrap.pack(side="left", fill="y")
        
        self._band_name_var = tk.StringVar(value=self.band.band_name)
        name_ent = tk.Entry(lbl_wrap, textvariable=self._band_name_var, font=FTXL, bg=BG, fg=TEXT,
                            relief="flat", bd=0, insertbackground=TEXT, width=12)
        name_ent.pack(side="left", anchor="center")
        tk.Label(lbl_wrap, text="📝", font=FT, bg=BG, fg=TEXT_DIM).pack(side="left", padx=6)

        def _on_name_change(*_):
            self.band.band_name = self._band_name_var.get()
            self.app.rename_band_tab(self)
        self._band_name_var.trace_add("write", _on_name_change)

        styled_button(hdr_bar, "🗑 Remove Band", lambda: self.app.remove_band_panel(self), fg=RED, bg=BG, hover_bg=BG3).pack(side="right", padx=4)

        # Dashboard Summary Metrics Widgets Block
        self._build_dashboard_metrics()

        # Integrated Control Strip (Navigation Pills Setup)
        ctrl_strip = tk.Frame(self, bg=BG)
        ctrl_strip.pack(fill="x", pady=10)

        self._pill_frame = tk.Frame(ctrl_strip, bg=BG)
        self._pill_frame.pack(side="left")

        self._sub_tabs = ["Inputs (52)", "Outputs (24)", "Stage Boxes", "Label View"]
        self._pill_buttons = {}
        self._active_sub_tab = "Inputs (52)"

        for t in self._sub_tabs:
            btn = styled_button(self._pill_frame, f"  {t}  ", lambda idx=t: self._switch_sub_tab(idx),
                                fg=TEXT_DIM, bg=BG, hover_bg=BG2)
            btn.pack(side="left", padx=2)
            self._pill_buttons[t] = btn

        # Modern Search Block Filter Layout Widget
        self._search_bar_frame = tk.Frame(self, bg=BG)
        self._search_bar_frame.pack(fill="x", pady=(0, 8))
        
        search_wrapper = tk.Frame(self._search_bar_frame, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        search_wrapper.pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Label(search_wrapper, text="  🔍 ", bg=BG2, fg=TEXT_DIM).pack(side="left")
        
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_updated)
        search_ent = tk.Entry(search_wrapper, textvariable=self._search_var, font=FT, bg=BG2, fg=TEXT,
                              relief="flat", bd=0, insertbackground=TEXT)
        search_ent.pack(side="left", fill="x", expand=True, ipady=6, padx=4)

        self._tools_wrapper = tk.Frame(self._search_bar_frame, bg=BG)
        self._tools_wrapper.pack(side="right")
        self._btn_auto = styled_button(self._tools_wrapper, "⚡ Auto-Name", self._autonumber_inputs, fg=TEXT, bg=BG3)
        self._btn_auto.pack(side="left", padx=4)
        self._btn_clear = styled_button(self._tools_wrapper, "🗑 Clear Sheet", self._clear_active_sheet, fg=RED, bg=BG3)
        self._btn_clear.pack(side="left", padx=4)

        # Worksheets Workspace Panels Container
        self._sheet_container = tk.Frame(self, bg=BG)
        self._sheet_container.pack(fill="both", expand=True)

        self._tab_inputs = tk.Frame(self._sheet_container, bg=BG)
        self._tab_outputs = tk.Frame(self._sheet_container, bg=BG)
        self._tab_boxes = tk.Frame(self._sheet_container, bg=BG)
        self._tab_labels = tk.Frame(self._sheet_container, bg=BG)

        self._build_inputs_tab()
        self._build_outputs_tab()
        self._build_boxes_tab()
        self._build_labels_tab()

        self._switch_sub_tab("Inputs (52)")

    def _build_dashboard_metrics(self):
        dash = tk.Frame(self, bg=BG)
        dash.pack(fill="x", pady=(0, 12))
        dash.columnconfigure((0, 1, 2, 3), weight=1, uniform="dash")

        def create_metric_card(parent, col, title, value, label, clr):
            c = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
            c.grid(row=0, column=col, sticky="nsew", padx=4, pady=4)
            left_strip = tk.Frame(c, bg=clr, width=4)
            left_strip.pack(side="left", fill="y")
            cnt = tk.Frame(c, bg=BG2, padx=12, pady=10)
            cnt.pack(side="left", fill="both", expand=True)
            tk.Label(cnt, text=title.upper(), font=FTX, bg=BG2, fg=TEXT_DIM).pack(anchor="w")
            r = tk.Frame(cnt, bg=BG2)
            r.pack(anchor="w", fill="x", expand=True)
            tk.Label(r, text=value, font=FTXL, bg=BG2, fg=TEXT).pack(side="left", anchor="s")
            tk.Label(r, text=f"  {label}", font=FTS, bg=BG2, fg=TEXT_DIM).pack(side="left", anchor="s", pady=2)
            return c

        create_metric_card(dash, 0, "Input Matrix", "52", "Mapped Channels", ACCENT)
        create_metric_card(dash, 1, "Output Matrix", "24", "Configured Lines", ACCENT2)
        create_metric_card(dash, 2, "Stage Routing", str(len(self.band.box_order)), "Active Dropboxes", GREEN)
        
        # Missing label engine calculation check card
        missing_count = sum(1 for ch in self.band.inputs if not ch["name"]) + sum(1 for ch in self.band.outputs if not ch["name"])
        self._missing_card = create_metric_card(dash, 3, "Sanity Check", str(missing_count), "Unlabeled Targets", YELLOW if missing_count > 0 else TEXT_DIM)

    def _switch_sub_tab(self, key):
        self._active_sub_tab = key
        for k, btn in self._pill_buttons.items():
            if k == key:
                btn.configure(bg=BG2, fg=ACCENT)
            else:
                btn.configure(bg=BG, fg=TEXT_DIM)

        for w in (self._tab_inputs, self._tab_outputs, self._tab_boxes, self._tab_labels):
            w.pack_forget()

        if key == "Inputs (52)":
            self._tab_inputs.pack(fill="both", expand=True)
            self._search_bar_frame.pack(fill="x", pady=(0, 8))
            self._btn_auto.pack(side="left", padx=4)
        elif key == "Outputs (24)":
            self._tab_outputs.pack(fill="both", expand=True)
            self._search_bar_frame.pack(fill="x", pady=(0, 8))
            self._btn_auto.pack_forget()
        elif key == "Stage Boxes":
            self._tab_boxes.pack(fill="both", expand=True)
            self._search_bar_frame.pack_forget()
            self._refresh_box_patch_labels()
        elif key == "Label View":
            self._tab_labels.pack(fill="both", expand=True)
            self._search_bar_frame.pack_forget()
            self._refresh_labels()

    def _on_search_updated(self, *_):
        self._search_query = self._search_var.get().lower().strip()
        if self._active_sub_tab == "Inputs (52)":
            self._render_filtered_inputs()
        elif self._active_sub_tab == "Outputs (24)":
            self._render_filtered_outputs()

    # ═══════════════════════════════════════════
    #  INPUT RENDER ENGINE
    # ═══════════════════════════════════════════
    def _build_inputs_tab(self):
        tab = self._tab_inputs
        _, _, inner = make_scrollable(tab)
        self._inputs_inner_layout = inner

        hrow = tk.Frame(inner, bg=BG)
        hrow.pack(fill="x", pady=(4, 6))
        for txt, w in [("CH", 5), ("CHANNEL NAME", 28), ("STAGE ROUTING BOX", 22), ("SOCKET", 10), ("TYPE", 8), ("LOCATION NOTES", 20)]:
            tk.Label(hrow, text=txt, font=FTB, bg=BG, fg=TEXT_DIM, width=w, anchor="w").pack(side="left", padx=4)

        self._input_rows = []
        for i in range(NUM_INPUTS):
            self._input_rows.append(self._make_input_row(inner, i))

    def _make_input_row(self, parent, idx):
        d = self.band.inputs[idx]
        bg = BG2

        frame = tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=BORDER)
        
        ch_badge = tk.Label(frame, text=f"{idx+1:02d}", font=FTB, bg=BORDER, fg=TEXT, width=4)
        ch_badge.pack(side="left", padx=6, pady=4)

        name_var = tk.StringVar(value=d["name"])
        name_ent = tk.Entry(frame, textvariable=name_var, font=FT, bg=BG3, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0, width=24)
        name_ent.pack(side="left", padx=6, pady=4, ipady=4)

        box_var = tk.StringVar(value=d["box"])
        box_cb = ttk.Combobox(frame, textvariable=box_var, values=self.band.box_choices(), state="readonly", width=16)
        box_cb.pack(side="left", padx=6, pady=4)

        socket_var = tk.StringVar(value="none" if d["socket"] == 0 else f"S{d['socket']:02d}")
        socket_cb = ttk.Combobox(frame, textvariable=socket_var, state="readonly", width=8)
        socket_cb.pack(side="left", padx=6, pady=4)

        dir_lbl = tk.Label(frame, text="IN", font=FTB, bg=GREEN, fg=DARK_TXT, width=5)
        dir_lbl.pack(side="left", padx=8, pady=4)

        loc_var = tk.StringVar(value=d.get("location", ""))
        loc_ent = tk.Entry(frame, textvariable=loc_var, font=FTS, bg=BG3, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0, width=18)
        loc_ent.pack(side="left", padx=6, pady=4, ipady=4)

        note_var = tk.StringVar(value=d["note"])
        note_ent = tk.Entry(frame, textvariable=note_var, font=FTS, bg=BG3, fg=TEXT_DIM, insertbackground=TEXT, relief="flat", bd=0, width=24)
        note_ent.pack(side="left", padx=6, pady=4, ipady=4, fill="x", expand=True)

        row = {"name": name_var, "box": box_var, "box_cb": box_cb, "socket": socket_var, "socket_cb": socket_cb,
               "dir_lbl": dir_lbl, "location": loc_var, "note": note_var, "frame": frame, "ch_badge": ch_badge}

        def _refresh_sockets(*_, r=row, i=idx):
            if self._building or self._updating: return
            self._fill_input_sockets(r)
            self._sync_input_data(r, i)

        def _on_socket(*_, r=row, i=idx):
            if self._building or self._updating: return
            self._sync_input_data(r, i)

        box_var.trace_add("write", _refresh_sockets)
        socket_var.trace_add("write", _on_socket)
        for v in (name_var, loc_var, note_var):
            v.trace_add("write", lambda *_, r=row, i=idx: self._sync_input_data(r, i))

        return row

    def _render_filtered_inputs(self):
        for row in self._input_rows:
            q = self._search_query
            if not q or q in row["name"].get().lower() or q in row["location"].get().lower() or q in row["note"].get().lower():
                row["frame"].pack(fill="x", pady=2)
            else:
                row["frame"].pack_forget()

    def _fill_input_sockets(self, row):
        box = row["box"].get()
        cur = row["socket"].get().replace("S", "")
        opts = ["none"]
        if box in self.band.boxes:
            for s in range(1, NUM_SOCKETS + 1):
                if self.band.get_socket_mode(box, s) != "IN": continue
                if not self.band.is_socket_assigned(box, s) or str(s) == cur:
                    opts.append(f"S{s:02d}")
        row["socket_cb"]["values"] = opts
        row["socket_cb"].set(f"S{int(cur):02d}" if cur.isdigit() and f"S{int(cur):02d}" in opts else "none")

    def _sync_input_data(self, row, idx):
        if self._updating: return
        self._updating = True
        try:
            sv = row["socket"].get().replace("S", "")
            new_box = row["box"].get()
            new_sock = 0 if sv == "none" or not sv.isdigit() else int(sv)

            old_box = self.band.inputs[idx]["box"]
            old_sock = self.band.inputs[idx]["socket"]
            if old_box != "---" and old_sock > 0: self.band.set_socket_assigned(old_box, old_sock, False)

            self.band.inputs[idx]["name"] = row["name"].get()
            self.band.inputs[idx]["box"] = new_box
            self.band.inputs[idx]["socket"] = new_sock
            self.band.inputs[idx]["location"] = row["location"].get()
            self.band.inputs[idx]["note"] = row["note"].get()

            if new_box != "---" and new_sock > 0: self.band.set_socket_assigned(new_box, new_sock, True)
            self._refresh_all_socket_dropdowns(exclude_input=idx)
        finally:
            self._updating = False

    # ═══════════════════════════════════════════
    #  OUTPUT RENDER ENGINE
    # ═══════════════════════════════════════════
    def _build_outputs_tab(self):
        tab = self._tab_outputs
        _, _, inner = make_scrollable(tab)
        self._outputs_inner_layout = inner

        hrow = tk.Frame(inner, bg=BG)
        hrow.pack(fill="x", pady=(4, 6))
        for txt, w in [("OUT", 5), ("OUTPUT NAME", 24), ("SIGNAL TYPE", 14), ("STAGE BOX", 16), ("SOCKET", 10), ("LOCATION NOTES", 24)]:
            tk.Label(hrow, text=txt, font=FTB, bg=BG, fg=TEXT_DIM, width=w, anchor="w").pack(side="left", padx=4)

        self._output_rows = []
        for i in range(NUM_OUTPUTS):
            self._output_rows.append(self._make_output_row(inner, i))

    def _make_output_row(self, parent, idx):
        d = self.band.outputs[idx]
        bg = BG2

        frame = tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=BORDER)

        ch_badge = tk.Label(frame, text=f"{idx+1:02d}", font=FTB, bg=ACCENT2, fg=DARK_TXT, width=4)
        ch_badge.pack(side="left", padx=6, pady=4)

        name_var = tk.StringVar(value=d["name"])
        name_ent = tk.Entry(frame, textvariable=name_var, font=FT, bg=BG3, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0, width=22)
        name_ent.pack(side="left", padx=6, pady=4, ipady=4)

        type_var = tk.StringVar(value=d["type"])
        type_cb = ttk.Combobox(frame, textvariable=type_var, values=OUTPUT_TYPES, state="readonly", width=12)
        type_cb.pack(side="left", padx=6, pady=4)

        box_var = tk.StringVar(value=d["box"])
        box_cb = ttk.Combobox(frame, textvariable=box_var, values=self.band.box_choices(), state="readonly", width=14)
        box_cb.pack(side="left", padx=6, pady=4)

        socket_var = tk.StringVar(value="none" if d["socket"] == 0 else f"S{d['socket']:02d}")
        socket_cb = ttk.Combobox(frame, textvariable=socket_var, state="readonly", width=8)
        socket_cb.pack(side="left", padx=6, pady=4)

        loc_var = tk.StringVar(value=d.get("location", ""))
        loc_ent = tk.Entry(frame, textvariable=loc_var, font=FTS, bg=BG3, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0, width=20)
        loc_ent.pack(side="left", padx=6, pady=4, ipady=4)

        note_var = tk.StringVar(value=d["note"])
        note_ent = tk.Entry(frame, textvariable=note_var, font=FTS, bg=BG3, fg=TEXT_DIM, insertbackground=TEXT, relief="flat", bd=0, width=22)
        note_ent.pack(side="left", padx=6, pady=4, ipady=4, fill="x", expand=True)

        row = {"name": name_var, "type": type_var, "box": box_var, "box_cb": box_cb, "socket": socket_var,
               "socket_cb": socket_cb, "location": loc_var, "note": note_var, "frame": frame}

        def _refresh_sockets(*_, r=row, i=idx):
            if self._building or self._updating: return
            self._fill_output_sockets(r)
            self._sync_output_data(r, i)

        box_var.trace_add("write", _refresh_sockets)
        socket_var.trace_add("write", lambda *_, r=row, i=idx: self._sync_output_data(r, i))
        for v in (name_var, type_var, loc_var, note_var):
            v.trace_add("write", lambda *_, r=row, i=idx: self._sync_output_data(r, i))

        return row

    def _render_filtered_outputs(self):
        for row in self._output_rows:
            q = self._search_query
            if not q or q in row["name"].get().lower() or q in row["location"].get().lower():
                row["frame"].pack(fill="x", pady=2)
            else:
                row["frame"].pack_forget()

    def _fill_output_sockets(self, row):
        box = row["box"].get()
        cur = row["socket"].get().replace("S", "")
        opts = ["none"]
        if box in self.band.boxes:
            for s in range(1, NUM_SOCKETS + 1):
                if self.band.get_socket_mode(box, s) != "OUT": continue
                if not self.band.is_socket_assigned(box, s) or str(s) == cur:
                    opts.append(f"S{s:02d}")
        row["socket_cb"]["values"] = opts
        row["socket_cb"].set(f"S{int(cur):02d}" if cur.isdigit() and f"S{int(cur):02d}" in opts else "none")

    def _sync_output_data(self, row, idx):
        if self._updating: return
        self._updating = True
        try:
            sv = row["socket"].get().replace("S", "")
            new_box = row["box"].get()
            new_sock = 0 if sv == "none" or not sv.isdigit() else int(sv)

            old_box = self.band.outputs[idx]["box"]
            old_sock = self.band.outputs[idx]["socket"]
            if old_box != "---" and old_sock > 0: self.band.set_socket_assigned(old_box, old_sock, False)

            self.band.outputs[idx]["name"] = row["name"].get()
            self.band.outputs[idx]["type"] = row["type"].get()
            self.band.outputs[idx]["box"] = new_box
            self.band.outputs[idx]["socket"] = new_sock
            self.band.outputs[idx]["location"] = row["location"].get()
            self.band.outputs[idx]["note"] = row["note"].get()

            if new_box != "---" and new_sock > 0: self.band.set_socket_assigned(new_box, new_sock, True)
            self._refresh_all_socket_dropdowns(exclude_output=idx)
        finally:
            self._updating = False

    # ═══════════════════════════════════════════
    #  STAGE ROUTING BOXES LABELS MANAGEMENT
    # ═══════════════════════════════════════════
    def _build_boxes_tab(self):
        self._patch_labels = {}
        tab = self._tab_boxes
        
        top_bar = tk.Frame(tab, bg=BG)
        top_bar.pack(fill="x", pady=4)
        tk.Label(top_bar, text="STAGE HARDWARE CONFIGURATION", font=FTB, bg=BG, fg=TEXT_DIM).pack(side="left")
        styled_button(top_bar, "➕ Add Stage Dropbox Hardware", self._add_stage_box, fg=GREEN, bg=BG3).pack(side="right")

        _, _, inner = make_scrollable(tab, horizontal=True)

        for bi, box_name in enumerate(self.band.box_order):
            col = bi % 4
            row_s = (bi // 4) * 15
            inner.columnconfigure(col, weight=1)

            card = tk.Frame(inner, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
            card.grid(row=row_s, column=col, padx=8, pady=8, sticky="nsew")

            hdr = tk.Frame(card, bg=BG3, padx=8, pady=6)
            hdr.pack(fill="x")
            
            bname_var = tk.StringVar(value=self.band.boxes[box_name]["name"])
            tk.Entry(hdr, textvariable=bname_var, font=FTB, bg=BG3, fg=TEXT, relief="flat", bd=0, width=16).pack(side="left")
            
            def _save_box_name(*_, bn=box_name, v=bname_var):
                self.band.boxes[bn]["name"] = v.get()
                self.app.sync_right_sidebar_preview()
            bname_var.trace_add("write", _save_box_name)

            for si in range(NUM_SOCKETS):
                snum = si + 1
                is_flex = snum >= FLEX_START
                mode = self.band.boxes[box_name]["socket_mode"][si]
                
                sf = tk.Frame(card, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
                sf.pack(fill="x", padx=6, pady=2)

                b_clr = GREEN if mode == "IN" else OUT_CLR
                sn_lbl = tk.Label(sf, text=f"S{snum:02d}", font=FTX, bg=b_clr, fg=DARK_TXT, width=5)
                sn_lbl.pack(side="left", padx=4, pady=4)

                if is_flex:
                    m_var = tk.StringVar(value=mode)
                    btn = tk.Button(sf, text=mode, font=FTX, width=5, bg=b_clr, fg=DARK_TXT, relief="flat", bd=0, cursor="hand2")

                    def _toggle_mode_cmd(bn=box_name, sn=snum, mv=m_var, b=btn, sl=sn_lbl):
                        def _exec():
                            nxt = "OUT" if mv.get() == "IN" else "IN"
                            c = GREEN if nxt == "IN" else OUT_CLR
                            mv.set(nxt)
                            b.config(text=nxt, bg=c)
                            sl.config(bg=c)
                            self.band.set_socket_mode(bn, sn, nxt)
                            self._on_socket_mode_change()
                        return _exec

                    btn.config(command=_toggle_mode_cmd())
                    btn.pack(side="left", padx=4)
                else:
                    tk.Label(sf, text="FIXED", font=FTX, bg=BG2, fg=TEXT_DIM).pack(side="left", padx=6)

                pl = tk.Label(sf, text="", font=FTX, bg=BG2, fg=TEXT, anchor="w")
                pl.pack(side="left", padx=8, fill="x", expand=True)
                self._patch_labels[(box_name, snum)] = pl

    def _add_stage_box(self):
        let = self.band.add_box()
        if not let: return
        choices = self.band.box_choices()
        for r in self._input_rows: r["box_cb"]["values"] = choices
        for r in self._output_rows: r["box_cb"]["values"] = choices
        for w in self._tab_boxes.winfo_children(): w.destroy()
        self._build_boxes_tab()
        self.app.sync_right_sidebar_preview()

    def _on_socket_mode_change(self):
        for r in self._input_rows: self._fill_input_sockets(r)
        for r in self._output_rows: self._fill_output_sockets(r)
        self._refresh_box_patch_labels()
        self.app.sync_right_sidebar_preview()

    def _refresh_box_patch_labels(self):
        lookup = {}
        for i, ch in enumerate(self.band.inputs):
            if ch["box"] != "---" and ch["socket"] > 0: lookup[(ch["box"], ch["socket"])] = f"I{i+1:02d} {ch['name']}"
        for i, ch in enumerate(self.band.outputs):
            if ch["box"] != "---" and ch["socket"] > 0: lookup[(ch["box"], ch["socket"])] = f"O{i+1:02d} {ch['name']}"

        for (box, snum), widget in self._patch_labels.items():
            widget.config(text=lookup.get((box, snum), ""))

    # ═══════════════════════════════════════════
    #  LOCAL SHEET LABEL VISUALIZATION OVERVIEW
    # ═══════════════════════════════════════════
    def _build_labels_tab(self):
        tab = self._tab_labels
        body = tk.Frame(tab, bg=BG)
        body.pack(fill="both", expand=True)
        body.columnconfigure((0, 1), weight=1, uniform="lbls")
        
        # Split mapping matrix architecture display system 
        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=6)
        tk.Label(left, text="STAGE HARDWARE MAPS", font=FTB, bg=BG, fg=ACCENT).pack(anchor="w", pady=4)
        self._sb_inner, _ = make_scrollframe(left)

        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew", padx=6)
        tk.Label(right, text="OUTPUT LINES INDEX", font=FTB, bg=BG, fg=ACCENT2).pack(anchor="w", pady=4)
        self._out_inner, _ = make_scrollframe(right)

    def _refresh_labels(self):
        for w in self._sb_inner.winfo_children(): w.destroy()
        for w in self._out_inner.winfo_children(): w.destroy()

        pm = {}
        for i, ch in enumerate(self.band.inputs):
            if ch["box"] != "---" and ch["socket"] > 0: pm[(ch["box"], ch["socket"])] = (i + 1, ch["name"], "IN")
        for i, ch in enumerate(self.band.outputs):
            if ch["box"] != "---" and ch["socket"] > 0: pm[(ch["box"], ch["socket"])] = (i + 1, ch["name"], "OUT")

        for box_name in self.band.box_order:
            bd = self.band.boxes[box_name]
            f = tk.Frame(self._sb_inner, bg=BG3, highlightthickness=1, highlightbackground=BORDER)
            f.pack(fill="x", pady=4, padx=4)
            tk.Label(f, text=bd.get("name", box_name), font=FTB, bg=BG3, fg=TEXT).pack(anchor="w", padx=8, pady=4)
            
            for si in range(NUM_SOCKETS):
                snum = si + 1
                key = (box_name, snum)
                if key in pm:
                    cnum, cname, kind = pm[key]
                    s_bg = GREEN if kind == "IN" else OUT_CLR
                    r = tk.Frame(f, bg=BG2)
                    r.pack(fill="x", padx=6, pady=1)
                    tk.Label(r, text=f"S{snum:02d}", font=FTX, bg=s_bg, fg=DARK_TXT, width=4).pack(side="left")
                    tk.Label(r, text=f" [{kind}] CH {cnum:02d} - {cname or 'Unnamed'}", font=FTS, bg=BG2, fg=TEXT, anchor="w").pack(side="left", padx=6)

        for i, out in enumerate(self.band.outputs):
            r = tk.Frame(self._out_inner, bg=BG3, highlightthickness=1, highlightbackground=BORDER)
            r.pack(fill="x", pady=2, padx=4)
            tk.Label(r, text=f"{i+1:02d}", font=FTB, bg=ACCENT2, fg=DARK_TXT, width=4).pack(side="left", padx=4, pady=4)
            tk.Label(r, text=out["name"] or "Empty Master Line", font=FT, bg=BG3, fg=TEXT, anchor="w").pack(side="left", padx=6)
            if out["box"] != "---" and out["socket"] > 0:
                tk.Label(r, text=f" ➔ Box {out['box']} S{out['socket']:02d}", font=FTX, bg=BORDER, fg=OUT_CLR).pack(side="right", padx=6)

    def _refresh_all_socket_dropdowns(self, exclude_input=None, exclude_output=None):
        if self._building or self._updating: return
        self._updating = True
        try:
            for i, r in enumerate(getattr(self, "_input_rows", [])):
                if i != exclude_input: self._fill_input_sockets(r)
            for i, r in enumerate(getattr(self, "_output_rows", [])):
                if i != exclude_output: self._fill_output_sockets(r)
            self._render_filtered_inputs()
            self._render_filtered_outputs()
            self.app.sync_right_sidebar_preview()
        finally:
            self._updating = False

    def _refresh_all(self):
        self._updating = True
        try:
            self.band.rebuild_assigned_from_data()
            for i, r in enumerate(self._input_rows):
                d = self.band.inputs[i]
                r["name"].set(d["name"])
                r["box"].set(d["box"])
                r["location"].set(d.get("location", ""))
                r["note"].set(d["note"])
                self._fill_input_sockets(r)
            for i, r in enumerate(self._output_rows):
                d = self.band.outputs[i]
                r["name"].set(d["name"])
                r["type"].set(d["type"])
                r["box"].set(d["box"])
                r["location"].set(d.get("location", ""))
                r["note"].set(d["note"])
                self._fill_output_sockets(r)
            self._band_name_var.set(self.band.band_name)
            self._render_filtered_inputs()
            self._render_filtered_outputs()
        finally:
            self._updating = False

    def _clear_active_sheet(self):
        if self._active_sub_tab == "Inputs (52)":
            for i in range(NUM_INPUTS): self.band.inputs[i] = {"name": "", "box": "---", "socket": 0, "location": "", "note": ""}
        elif self._active_sub_tab == "Outputs (24)":
            for i in range(NUM_OUTPUTS): self.band.outputs[i] = {"name": "", "type": "---", "box": "---", "socket": 0, "location": "", "note": ""}
        self._refresh_all()
        self.app.sync_right_sidebar_preview()

    def _autonumber_inputs(self):
        for i, r in enumerate(self._input_rows):
            if not r["name"].get(): r["name"].set(f"Input {i+1:02d}")


# ─────────────────────────────────────────────
#  Settings Live Sync Management Interface Panel
# ─────────────────────────────────────────────
class SettingsPanel(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self.sync = app.sync

        self._port_var = tk.StringVar(value=str(SYNC_DEFAULT_PORT))
        self._host_ip_var = tk.StringVar(value="")
        self._client_port_var = tk.StringVar(value=str(SYNC_DEFAULT_PORT))
        self._status_var = tk.StringVar(value="● Offline")

        self._build()
        self._refresh_loop()

    def _build(self):
        wrap = tk.Frame(self, bg=BG)
        wrap.pack(fill="both", expand=True, padx=32, pady=24)

        tk.Label(wrap, text="⚙ Hardware Settings & Network Node Sync", font=FTTL, bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 16))

        cards = tk.Frame(wrap, bg=BG)
        cards.pack(fill="x")
        cards.columnconfigure((0, 1), weight=1, uniform="set")

        h_card = make_card(cards, "🖥 Host Network Matrix Session", "Allows client mixing desks or stage manager terminals to mirror your configuration live.", accent=GREEN)
        h_card.grid(row=0, column=0, sticky="nsew", padx=6)
        
        r1 = tk.Frame(h_card, bg=BG2)
        r1.pack(fill="x", padx=16, pady=4)
        tk.Label(r1, text="Hosting Port: ", font=FTS, bg=BG2, fg=TEXT_DIM).pack(side="left")
        tk.Entry(r1, textvariable=self._port_var, font=FT, bg=BG3, fg=TEXT, relief="flat", bd=0, width=8).pack(side="left", ipady=3)
        styled_button(h_card, "Initialize Session Server", self._start_host, fg=GREEN, bg=BG3).pack(anchor="w", padx=16, pady=12)
        self._host_info = tk.Label(h_card, text="", font=FTS, bg=BG2, fg=TEXT_DIM, justify="left")
        self._host_info.pack(anchor="w", padx=16, pady=4)

        c_card = make_card(cards, "🔗 Connect to Session Server Node", "Pull terminal master sync routing matrix states directly into this hardware machine instance.", accent=ACCENT)
        c_card.grid(row=0, column=1, sticky="nsew", padx=6)
        
        r2 = tk.Frame(c_card, bg=BG2)
        r2.pack(fill="x", padx=16, pady=4)
        tk.Label(r2, text="Host IP Node: ", font=FTS, bg=BG2, fg=TEXT_DIM).pack(side="left")
        tk.Entry(r2, textvariable=self._host_ip_var, font=FT, bg=BG3, fg=TEXT, relief="flat", bd=0, width=16).pack(side="left", ipady=3)
        
        r3 = tk.Frame(c_card, bg=BG2)
        r3.pack(fill="x", padx=16, pady=4)
        tk.Label(r3, text="Session Port: ", font=FTS, bg=BG2, fg=TEXT_DIM).pack(side="left")
        tk.Entry(r3, textvariable=self._client_port_var, font=FT, bg=BG3, fg=TEXT, relief="flat", bd=0, width=8).pack(side="left", ipady=3)
        
        styled_button(c_card, "Join Active Cluster", self._start_client, fg=ACCENT, bg=BG3).pack(anchor="w", padx=16, pady=12)

        s_card = make_card(wrap, "📡 Interface Connectivity Telemetry", None, accent=PURPLE)
        s_card.pack(fill="x", pady=16)
        sb = tk.Frame(s_card, bg=BG2, padx=16, pady=12)
        sb.pack(fill="x")
        self._status_lbl = tk.Label(sb, textvariable=self._status_var, font=FTB, bg=BG2, fg=TEXT_DIM)
        self._status_lbl.pack(side="left")
        styled_button(sb, "Disconnect Terminal Connection", self._stop_sync, fg=RED, bg=BG3).pack(side="right")

    def _start_host(self):
        try: port = int(self._port_var.get())
        except ValueError: return
        if self.sync.start_host(port):
            self._host_info.configure(text=f"Network Node Target Broadcasting at:\n{get_local_ip()} : {port}")

    def _start_client(self):
        ip = self._host_ip_var.get().strip()
        try: port = int(self._client_port_var.get())
        except ValueError: return
        self.sync.start_client(ip, port)

    def _stop_sync(self):
        self.sync.stop()
        self._host_info.configure(text="")

    def _refresh_loop(self):
        m = self.sync.mode
        if m == "host":
            self._status_var.set(f"● SESSION HOST ACTIVE — {len(self.sync.client_conns)} Terminals Mirrors Connected")
            self._status_lbl.configure(fg=GREEN)
        elif m == "client":
            self._status_var.set(f"● SESSION STREAMING SYNC ACTIVE — {self.sync.role_status}")
            self._status_lbl.configure(fg=ACCENT)
        else:
            self._status_var.set("● OFFLINE INTERFACE DISCONNECTED")
            self._status_lbl.configure(fg=TEXT_DIM)
        self.app._update_sync_badge()
        self.after(1000, self._refresh_loop)


# ─────────────────────────────────────────────
#  Application Master Window Shell 
# ─────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.show = ShowData()
        self._band_panels = []
        self.all_labels_panel = None
        self.settings_panel = None
        self.sync = SyncManager(self)

        self._nav_items = {}       
        self._nav_pages = {}       
        self._active_nav_key = None

        self.title("PATCH MANAGER Pro — Stage Box & Routing Matrix Dashboard")
        self.configure(bg=BG)
        self.geometry("1600x950")
        self.minsize(1200, 750)

        self._apply_theme_specs()
        self._build_global_layout()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # START THE AUTOUPDATE TICKER REFRESH PIPELINE
        self._loop_autoupdate_engine()

    def _on_close(self):
        self.sync.stop()
        self.destroy()

    def _apply_theme_specs(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=TEXT, fieldbackground=BG3, bordercolor=BORDER, font=FT, borderwidth=0)
        
        s.configure("TCombobox", selectbackground=BG2, selectforeground=TEXT, background=BG3, foreground=TEXT, arrowcolor=TEXT_DIM, fieldbackground=BG3)
        s.map("TCombobox",
              fieldbackground=[("readonly", BG3), ("focus", BG3)],
              background=[("readonly", BG3), ("focus", BG3)],
              foreground=[("readonly", TEXT)],
              arrowcolor=[("active", TEXT), ("pressed", ACCENT2)])

    def _build_global_layout(self):
        # 1. APPLICATION TOP BAR HEADER MESH
        hdr = tk.Frame(self, bg=BG2, height=60, highlightthickness=1, highlightbackground=BORDER)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        l_bar = tk.Frame(hdr, bg=BG2)
        l_bar.pack(side="left", fill="y")
        
        tk.Label(l_bar, text=" 🎚 PATCH MANAGER", font=FTTL, bg=BG2, fg=TEXT).pack(side="left", padx=16)
        tk.Frame(l_bar, bg=BORDER, width=1).pack(side="left", fill="y", pady=12)

        tk.Label(l_bar, text="  SHOW INDEX:", font=FTX, bg=BG2, fg=TEXT_DIM).pack(side="left")
        self._show_name_var = tk.StringVar(value=self.show.show_name)
        tk.Entry(l_bar, textvariable=self._show_name_var, font=FTB, bg=BG3, fg=TEXT, relief="flat", bd=0, insertbackground=TEXT, width=20).pack(side="left", padx=6, ipady=4)

        self._sync_badge = tk.Label(l_bar, text=" ● OFFLINE ", font=FTB, bg=BG2, fg=TEXT_DIM)
        self._sync_badge.pack(side="left", padx=16)

        r_bar = tk.Frame(hdr, bg=BG2)
        r_bar.pack(side="right", fill="y", padx=16)
        styled_button(r_bar, "💾 Save Show", self._save, fg=GREEN, bg=BG3).pack(side="right", padx=4)
        styled_button(r_bar, "📂 Load Show", self._load, fg=YELLOW, bg=BG3).pack(side="right", padx=4)
        styled_button(r_bar, "🖨 Print Report", self._export_txt, fg=ACCENT, bg=BG3).pack(side="right", padx=4)

        # 2. THREE COLUMN SPLIT SYSTEM BODY ARCHITECTURE
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        # COLUMN A: NAVIGATION SIDEBAR (LEFT)
        self._sidebar = tk.Frame(body, bg=BG2, width=220, highlightthickness=1, highlightbackground=BORDER)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        sb_hdr = tk.Frame(self._sidebar, bg=BG2, padx=12, pady=12)
        sb_hdr.pack(fill="x")
        tk.Label(sb_hdr, text="BANDS INDEX SHEETS", font=FTX, bg=BG2, fg=TEXT_DIM).pack(side="left")
        styled_button(sb_hdr, " ➕ ", self._add_band, fg=GREEN, bg=BG3, padding=2).pack(side="right")

        self._band_tabs_sub_container = tk.Frame(self._sidebar, bg=BG2)
        self._band_tabs_sub_container.pack(fill="x")

        tk.Frame(self._sidebar, bg=BORDER, height=1).pack(fill="x", padx=12, pady=12)
        self._misc_nav_container = tk.Frame(self._sidebar, bg=BG2)
        self._misc_nav_container.pack(fill="x")
        self._make_nav_pill_button(self._misc_nav_container, "🌎 Global Overview", "all_labels", ACCENT)
        self._make_nav_pill_button(self._misc_nav_container, "⚙ Hardware Setup", "settings", PURPLE)

        # COLUMN C: SIDEBAR DISPLAY PANEL DISPLAY MATRIX (RIGHT)
        self._right_sidebar = tk.Frame(body, bg=BG2, width=320, highlightthickness=1, highlightbackground=BORDER)
        self._right_sidebar.pack(side="right", fill="y")
        self._right_sidebar.pack_propagate(False)
        
        rs_h = tk.Frame(self._right_sidebar, bg=BG2, padx=12, pady=12)
        rs_h.pack(fill="x")
        tk.Label(rs_h, text="STAGE HARDWARE FEED", font=FTB, bg=BG2, fg=TEXT).pack(side="left")
        
        styled_button(rs_h, "↻", lambda: self.sync_right_sidebar_preview(force=True), fg=TEXT, bg=BG3).pack(side="right", padx=2)
        styled_button(rs_h, "+ Box", self._trigger_active_panel_box_add, fg=ACCENT, bg=BG3).pack(side="right", padx=2)

        self._rs_inner, _ = make_scrollframe(self._right_sidebar)

        # COLUMN B: MAIN INTERACTIVE WORKSPACE VIEW (CENTER)
        self._content = tk.Frame(body, bg=BG, padx=16, pady=16)
        self._content.pack(side="left", fill="both", expand=True)

        self.settings_panel = SettingsPanel(self._content, self)
        self.settings_panel.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._nav_pages["settings"] = self.settings_panel

        self._rebuild_band_tabs()

    def _make_nav_pill_button(self, parent, text, key, accent_color):
        row = tk.Frame(parent, bg=BG2, cursor="hand2")
        row.pack(fill="x", padx=8, pady=3)
        lbl = tk.Label(row, text=text, font=FTB, bg=BG2, fg=TEXT_DIM, anchor="w", padx=8, pady=6)
        lbl.pack(fill="x", expand=True)

        for w in (row, lbl):
            w.bind("<Button-1>", lambda _e, k=key: self._nav_select(k))
        self._nav_items[key] = {"row": row, "lbl": lbl, "accent": accent_color}

    def _nav_select(self, key):
        if key not in self._nav_pages: return
        self._active_nav_key = key
        for k, item in self._nav_items.items():
            act = (k == key)
            item["row"].configure(bg=BG3 if act else BG2)
            item["lbl"].configure(bg=BG3 if act else BG2, fg=item["accent"] if act else TEXT_DIM)
        self._nav_pages[key].lift()
        
        if key == "all_labels":
            self.all_labels_panel.refresh_all_labels(force=True)
        else:
            self.sync_right_sidebar_preview(force=True)

    # ═══════════════════════════════════════════
    #  AUTOMATED BACKGROUND MONITOR LOOP
    # ═══════════════════════════════════════════
    def _loop_autoupdate_engine(self):
        """Dynamic background loop engine that refreshes the interface smoothly every 1.5 seconds[cite: 5]."""
        if self._active_nav_key == "all_labels":
            self.all_labels_panel.refresh_all_labels(force=False)
        else:
            self.sync_right_sidebar_preview(force=False)
            
        self.after(1500, self._loop_autoupdate_engine)

    def sync_right_sidebar_preview(self, force=False):
        """Modifies layout metrics dynamically in place to avoid flickering artifacts[cite: 5]."""
        if not hasattr(self, "_rs_cache"):
            self._rs_cache = {"key": None, "widgets": {}}
            
        if not self._active_nav_key or not self._active_nav_key.startswith("band:"):
            if self._rs_cache["key"] != "none":
                for w in self._rs_inner.winfo_children(): w.destroy()
                self._rs_cache = {"key": "none", "widgets": {}}
                tk.Label(self._rs_inner, text="Select active band layout\nto review stage patch arrays.", font=FTS, bg=BG2, fg=TEXT_DIM, justify="center").pack(pady=40, fill="x")
            return
            
        idx = int(self._active_nav_key.split(":")[1])
        b = self.show.bands[idx]

        pm = {}
        for i, ch in enumerate(b.inputs):
            if ch["box"] != "---" and ch["socket"] > 0: pm[(ch["box"], ch["socket"])] = (i+1, ch["name"], "IN")
        for i, ch in enumerate(b.outputs):
            if ch["box"] != "---" and ch["socket"] > 0: pm[(ch["box"], ch["socket"])] = (i+1, ch["name"], "OUT")

        current_structural_key = f"{self._active_nav_key}:{len(b.box_order)}"
        
        if self._rs_cache["key"] != current_structural_key or force:
            for w in self._rs_inner.winfo_children(): w.destroy()
            self._rs_cache = {"key": current_structural_key, "widgets": {}}
            
            for let in b.box_order:
                bd = b.boxes[let]
                card = tk.Frame(self._rs_inner, bg=BG3, highlightthickness=1, highlightbackground=BORDER)
                card.pack(fill="x", padx=10, pady=6)
                
                h = tk.Frame(card, bg=BG3, padx=6, pady=4)
                h.pack(fill="x")
                title_lbl = tk.Label(h, text=bd.get("name", f"Dropbox {let}"), font=FTB, bg=BG3, fg=TEXT)
                title_lbl.pack(side="left")
                
                self._rs_cache["widgets"][(let, "title")] = title_lbl
                
                for s in range(1, NUM_SOCKETS + 1):
                    r = tk.Frame(card, bg=BG3, padx=6, pady=1)
                    r.pack(fill="x")
                    
                    tk.Label(r, text=f"S{s:02d}", font=FTX, bg=BG2, fg=TEXT_DIM, width=4).pack(side="left")
                    m_lbl = tk.Label(r, text=" -- ", font=FTX, bg=BG2, fg=DARK_TXT)
                    m_lbl.pack(side="left", padx=4)
                    
                    t_lbl = tk.Label(r, text="-", font=FTX, bg=BG3, fg=TEXT, anchor="w")
                    t_lbl.pack(side="left", padx=4, fill="x", expand=True)
                    
                    self._rs_cache["widgets"][(let, s)] = (m_lbl, t_lbl)

        for let in b.box_order:
            bd = b.boxes[let]
            if (let, "title") in self._rs_cache["widgets"]:
                self._rs_cache["widgets"][(let, "title")].config(text=bd.get("name", f"Dropbox {let}"))
                
            for s in range(1, NUM_SOCKETS + 1):
                mode = bd["socket_mode"][s-1]
                lbl_clr = GREEN if mode == "IN" else OUT_CLR
                if (let, s) in self._rs_cache["widgets"]:
                    m_lbl, t_lbl = self._rs_cache["widgets"][(let, s)]
                    m_lbl.config(text=f" {mode} ", bg=lbl_clr)
                    
                    txt = "-"
                    if (let, s) in pm:
                        cnum, cname, kind = pm[(let, s)]
                        txt = f"CH {cnum:02d} - {cname}"
                    t_lbl.config(text=txt)

    def _trigger_active_panel_box_add(self):
        if self._active_nav_key and self._active_nav_key.startswith("band:"):
            idx = int(self._active_nav_key.split(":")[1])
            self._band_panels[idx]._add_stage_box()

    def _rebuild_band_tabs(self):
        for p in self._band_panels: p.destroy()
        for w in self._band_tabs_sub_container.winfo_children(): w.destroy()
        for k in list(self._nav_items.keys()):
            if k.startswith("band:"): del self._nav_items[k]; self._nav_pages.pop(k, None)

        self._band_panels = []
        for i, band in enumerate(self.show.bands):
            panel = BandPanel(self._content, self, band)
            panel.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._band_panels.append(panel)
            k = f"band:{i}"
            self._nav_pages[k] = panel
            self._make_nav_pill_button(self._band_tabs_sub_container, f"🎸 {band.band_name}", k, BOX_COLORS[i % len(BOX_COLORS)])

        self.all_labels_panel = AllLabelsPanel(self._content, self, self.show)
        self.all_labels_panel.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._nav_pages["all_labels"] = self.all_labels_panel

        target = self._active_nav_key if self._active_nav_key in self._nav_pages else "band:0"
        self._nav_select(target)

    def rename_band_tab(self, panel):
        if panel not in self._band_panels: return
        idx = self._band_panels.index(panel)
        item = self._nav_items.get(f"band:{idx}")
        if item: item["lbl"].configure(text=f"🎸 {panel.band.band_name}")

    def _add_band(self):
        sug = f"Band {len(self.show.bands) + 1}"
        name = simpledialog.askstring("Initialize New Set Sheet", "Band Sheet Name:", initialvalue=sug, parent=self)
        if not name: return
        self.show.add_band(name.strip())
        self._rebuild_band_tabs()
        self._nav_select(f"band:{len(self._band_panels)-1}")

    def remove_band_panel(self, panel):
        if len(self.show.bands) <= 1: return
        idx = self._band_panels.index(panel)
        if messagebox.askyesno("Purge Configuration", f"Delete sheet matrix '{panel.band.band_name}' permanent records?"):
            self.show.remove_band(idx)
            self._rebuild_band_tabs()
            self._nav_select("band:0")

    def _update_sync_badge(self):
        m = self.sync.mode
        if m == "host": self._sync_badge.configure(text=f" ● HOSTING CRADLE ({len(self.sync.client_conns)}) ", fg=GREEN)
        elif m == "client": self._sync_badge.configure(text=" ● CLUSTER COUPLING ACTIVE ", fg=ACCENT)
        else: self._sync_badge.configure(text=" ● OFFLINE ", fg=TEXT_DIM)

    def _apply_remote_show_update(self):
        self._rebuild_band_tabs()

    def _save(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Patch Record Map", "*.json")])
        if not path: return
        with open(path, "w") as f: json.dump(self.show.to_dict(), f, indent=2)

    def _load(self):
        path = filedialog.askopenfilename(filetypes=[("Patch Record Map", "*.json")])
        if not path: return
        with open(path) as f: self.show.from_dict(json.load(f))
        self._rebuild_band_tabs()

    def _export_txt(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Report Ledger", "*.txt")])
        if not path: return
        lines = [f"MASTER LEDGER INVENTORY REPORT - {self.show.show_name}\n" + "="*60]
        for b in self.show.bands: lines += build_band_report_lines(b)
        with open(path, "w", encoding="utf-8") as f: f.write("\n".join(lines))


# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()