# Stage Box & Audio Patch Manager — Documentation & Modification Guide

> **File:** `stagebox_manager_fixed_6_.py`  
> **Language:** Python 3 · **GUI Framework:** Tkinter (ttk)  
> **Persistence:** JSON save/load + plain-text export

---

## Table of Contents
1. [Overview](#1-overview)
2. [Architecture at a Glance](#2-architecture-at-a-glance)
3. [Constants Reference](#3-constants-reference)
4. [Data Model — `PatchData`](#4-data-model--patchdata)
5. [Theme & Colours](#5-theme--colours)
6. [App Class — UI Breakdown](#6-app-class--ui-breakdown)
   - 6.1 Inputs Tab
   - 6.2 Outputs Tab
   - 6.3 Stage Boxes Tab
   - 6.4 Label View Tab
7. [Key Internal Mechanisms](#7-key-internal-mechanisms)
8. [File I/O](#8-file-io)
9. [Common Modifications — Step-by-Step](#9-common-modifications--step-by-step)
   - 9.1 Change the number of input/output channels
   - 9.2 Add more stage boxes
   - 9.3 Change the number of sockets per box
   - 9.4 Add a new output type
   - 9.5 Add a new data field to inputs or outputs
   - 9.6 Change the colour scheme
   - 9.7 Change fonts
   - 9.8 Resize the window
   - 9.9 Add a new tab
   - 9.10 Add an import from CSV feature
10. [Troubleshooting Common Issues](#10-troubleshooting-common-issues)
11. [Dependency & Environment Notes](#11-dependency--environment-notes)

---

## 1. Overview

This application is a **live-sound patch management tool**. It lets an audio engineer plan and document how microphones and instruments (inputs) and monitor sends/records (outputs) are wired through physical **stage boxes** on stage.

**Core concept:**

- There are 7 **stage boxes** (A–G), each with 12 physical sockets.
- Sockets 1–8 are permanently wired as **inputs** (mic/line in from stage).
- Sockets 9–12 are **flexible** — each can be individually switched between input and output mode.
- Up to **52 input channels** and **24 output channels** can each be assigned to a specific box and socket.
- The app prevents double-booking: no two channels can share the same socket.

---

## 2. Architecture at a Glance

```
stagebox_manager_fixed_6_.py
│
├── Constants (top of file)
│   └── NUM_INPUTS, NUM_OUTPUTS, NUM_SOCKETS, box names, output types …
│
├── PatchData  (pure data model — no UI)
│   ├── inputs[]         list of 52 channel dicts
│   ├── outputs[]        list of 24 channel dicts
│   ├── boxes{}          dict of 7 stage box dicts
│   └── Methods: get/set socket mode, assign sockets, to_dict / from_dict
│
└── App(tk.Tk)  (entire GUI)
    ├── _apply_style()          ttk theme setup
    ├── _build_ui()             header bar + notebook with 4 tabs
    ├── _build_inputs_tab()     52-row input patch table
    ├── _build_outputs_tab()    24-row output patch table
    ├── _build_boxes_tab()      visual stage box grid with toggle buttons
    ├── _build_labels_tab()     read-only overview panel
    ├── _refresh_all()          sync PatchData → all UI widgets
    ├── _save() / _load()       JSON file I/O
    └── _export_txt()           formatted plain-text export
```

Data flow is **bidirectional but managed**:

- UI widgets hold `tk.StringVar` variables.
- `trace_add("write", …)` callbacks fire whenever a widget changes and call `_sync_input_data` / `_sync_output_data`, which write back to `PatchData`.
- A boolean flag `self._updating` prevents callback loops.

---

## 3. Constants Reference

All top-of-file constants that you are most likely to want to change:

| Constant | Default | Purpose |
|---|---|---|
| `NUM_INPUTS` | `52` | Total input channels in the table |
| `NUM_OUTPUTS` | `24` | Total output channels in the table |
| `NUM_SOCKETS` | `12` | Sockets per stage box |
| `FIXED_IN_COUNT` | `8` | How many sockets (1–N) are permanently INPUT |
| `FLEX_START` | `9` | First socket number that is switchable |
| `STAGE_BOX_NAMES` | `["A","B","C","D","E","F","G"]` | Box identifiers (drives everything) |
| `BOX_CHOICES` | `["---"] + STAGE_BOX_NAMES` | Dropdown values including empty |
| `OUTPUT_TYPES` | `["---","Aux","Auto-Tune IN","Record","Other"]` | Output type dropdown values |

---

## 4. Data Model — `PatchData`

### `_default_box(name)` — module-level helper

Creates a blank stage box dict:

```python
{
  "name": "A",                          # editable display name
  "socket_mode": ["IN","IN",...],       # list of 12 strings, index 0 = socket 1
  "socket_assigned": {1: False, ...}    # dict keyed by socket number (1-based)
}
```

### `PatchData` attributes

| Attribute | Type | Description |
|---|---|---|
| `inputs` | `list[dict]` | 52 items; each: `name, box, socket, note, location` |
| `outputs` | `list[dict]` | 24 items; each: `name, type, box, socket, note, location` |
| `boxes` | `dict` | Keyed by box letter A–G |
| `show_name` | `str` | The show/project name shown in the header |

### Key methods

| Method | What it does |
|---|---|
| `get_socket_mode(box, socket_num)` | Returns `"IN"` or `"OUT"` for any socket |
| `set_socket_mode(box, socket_num, mode)` | Writes mode; only allowed for socket ≥ `FLEX_START` |
| `is_socket_assigned(box, socket_num)` | Returns `True` if already patched |
| `set_socket_assigned(box, socket_num, value)` | Marks/unmarks a socket as taken |
| `rebuild_assigned_from_data()` | Recomputes all `socket_assigned` flags by scanning every channel |
| `to_dict()` | Serialise everything to a plain dict (for JSON) |
| `from_dict(d)` | Deserialise; also handles migration of older save files that lack `location` |

---

## 5. Theme & Colours

The app uses the **Gruvbox Dark** palette. All colour constants are at the top of the file:

```python
BG       = "#282828"   # main background
BG2      = "#32302f"   # toolbar / header backgrounds
BG3      = "#3c3836"   # widget fill / alternate row colour
BORDER   = "#504945"   # widget borders
TEXT     = "#ebdbb2"   # primary text
TEXT_DIM = "#928374"   # muted labels, column headers
ACCENT   = "#83a598"   # aqua — inputs, links
ACCENT2  = "#fe8019"   # orange — outputs
GREEN    = "#b8bb26"   # IN-mode sockets
YELLOW   = "#fabd2f"   # LOAD button, Auto-Name
RED      = "#fb4934"   # Clear buttons
PURPLE   = "#d3869b"   # Location fields
OUT_CLR  = "#fe8019"   # OUT-mode socket badges (same as ACCENT2)
```

`BOX_COLORS` is a 10-item list; each stage box gets a distinct colour cycling through this list.

Font constants:

```python
FT   = ("Courier New", 10)        # default body
FTS  = ("Courier New", 9)         # small / secondary
FTX  = ("Courier New", 8)         # extra small (socket badges)
FTB  = ("Courier New", 10, "bold")
FTH  = ("Courier New", 13, "bold") # section headings
FTTL = ("Courier New", 17, "bold") # main title
```

---

## 6. App Class — UI Breakdown

### 6.1 Inputs Tab (`_build_inputs_tab` / `_make_input_row`)

Builds a scrollable list of 52 rows. Each row is constructed by `_make_input_row(parent, idx)` and contains:

| Widget | Variable | Data field |
|---|---|---|
| Channel number badge (label) | — | `idx + 1` |
| Name entry | `name_var` | `inputs[i]["name"]` |
| Stage box combobox | `box_var` | `inputs[i]["box"]` |
| Socket combobox | `socket_var` | `inputs[i]["socket"]` |
| Direction label | `dir_lbl` | Computed from socket mode |
| Location entry | `location_var` | `inputs[i]["location"]` |
| Note entry | `note_var` | `inputs[i]["note"]` |

**Socket dropdown population** (`_fill_input_sockets`): Only shows sockets whose mode is `"IN"` and which are not already assigned — plus the one the row currently holds (so existing assignments stay selectable).

### 6.2 Outputs Tab (`_build_outputs_tab` / `_make_output_row`)

Same structure as inputs but with an extra **Type** combobox (`OUTPUT_TYPES`). Socket dropdown (`_fill_output_sockets`) filters to `"OUT"` mode sockets only.

### 6.3 Stage Boxes Tab (`_build_boxes_tab`)

Displays all 7 boxes in a grid (4 columns). For each box:

- An editable header shows the box name and letter.
- Each of the 12 sockets appears as a row with a colour-coded badge.
- Sockets 1–8 show a static `IN` label.
- Sockets 9–12 show a **toggle button** that flips between `IN` and `OUT` and calls `_on_socket_mode_change()`.
- A patch label (`self._patch_labels`) next to each socket shows which channel is patched there.

### 6.4 Label View Tab (`_build_labels_tab` / `_refresh_labels`)

A read-only overview, split into two columns:

- **Left:** Stage Box Labels — shows each box with all its sockets and assigned channel names.
- **Right:** Output Labels — compact list of all output channels with name, type, box/socket, and location.

This tab is rebuilt from scratch on every refresh (the "Refresh" button calls `_refresh_labels`), so it always reflects current data without needing live bindings.

---

## 7. Key Internal Mechanisms

### Recursion guard

```python
self._building = True   # set during __init__, prevents callbacks during setup
self._updating = False  # set during data-sync, prevents callback chains
```

Every callback starts with:

```python
if self._building or getattr(self, "_updating", False): return
```

When `_sync_input_data` runs, it sets `_updating = True` inside a `try/finally` block, does its work, then releases. This means changing one widget can trigger other socket dropdowns to update without causing infinite recursion.

### Socket assignment bookkeeping

Every time a channel's box or socket changes:

1. The **old** socket is unmarked: `set_socket_assigned(old_box, old_sock, False)`
2. The new values are written to `PatchData`.
3. The **new** socket is marked: `set_socket_assigned(new_box, new_sock, True)`
4. `_refresh_all_socket_dropdowns(exclude_input=idx)` is called so every *other* row's socket dropdown updates to reflect the newly freed/taken socket.

On load or clear, `rebuild_assigned_from_data()` recomputes everything from scratch rather than relying on incremental bookkeeping.

---

## 8. File I/O

### Save (JSON)

`_save()` calls `PatchData.to_dict()` and `json.dump`s it to a `.json` file chosen via a file dialog.

The JSON structure is:

```json
{
  "show_name": "My Show",
  "inputs": [ { "name": "Kick", "box": "A", "socket": 1, "note": "", "location": "Drums" }, ... ],
  "outputs": [ { "name": "Drummer IEM", "type": "Aux", "box": "A", "socket": 9, "note": "", "location": "" }, ... ],
  "boxes": {
    "A": { "name": "A", "socket_mode": ["IN","IN",...,"OUT",...], "socket_assigned": { "1": true, ... } },
    ...
  }
}
```

### Load (JSON)

`_load()` calls `PatchData.from_dict()` which also **migrates** older saves:

- Adds a blank `"location"` field to any channel that lacks one.
- Pads short `socket_mode` arrays.
- Ensures `socket_assigned` exists on every box.

### Export (plain text)

`_export_txt()` writes a human-readable `.txt` file with four sections:

1. Stage box socket config table
2. Input patch list
3. Output patch list
4. Per-box label block with ASCII-art box borders
5. Output label block

---

## 9. Common Modifications — Step-by-Step

### 9.1 Change the number of input or output channels

Find the constants at the top of the file and change them:

```python
NUM_INPUTS  = 52   # ← change to e.g. 64
NUM_OUTPUTS = 24   # ← change to e.g. 32
```

The tab headers in `_build_ui` have hard-coded counts in the text — update them too:

```python
self._nb.add(self._tab_inputs,  text="  INPUTS (52)  ")   # → (64)
self._nb.add(self._tab_outputs, text="  OUTPUTS (24)  ")   # → (32)
```

And the toolbar label in `_build_inputs_tab`:

```python
tk.Label(bar, text="  INPUT PATCH  - 52 Channels", ...)    # → 64 Channels
```

No other changes needed — the loop `for i in range(NUM_INPUTS)` picks up the new value automatically.

---

### 9.2 Add more stage boxes

1. Add letters to `STAGE_BOX_NAMES`:

```python
STAGE_BOX_NAMES = [f"{c}" for c in "ABCDEFGH"]   # added H
```

That's it. `BOX_CHOICES`, `PatchData.boxes`, and all UI loops derive from this list. If you add more than 10 boxes, also extend `BOX_COLORS` so each box gets a distinct colour.

---

### 9.3 Change the number of sockets per box

Adjust the constants:

```python
NUM_SOCKETS    = 16   # total sockets per box
FIXED_IN_COUNT = 12   # sockets 1–12 always INPUT
FLEX_START     = 13   # sockets 13–16 are switchable
```

Existing save files will be migrated on load (the `from_dict` method pads short `socket_mode` arrays).

---

### 9.4 Add a new output type

Find `OUTPUT_TYPES` near the top:

```python
OUTPUT_TYPES = ["---", "Aux", "Auto-Tune IN", "Record", "Other"]
```

Add your new type to this list:

```python
OUTPUT_TYPES = ["---", "Aux", "Auto-Tune IN", "Record", "IEM", "Other"]
```

The combobox in every output row is populated from this list, so the new option appears immediately on next launch.

---

### 9.5 Add a new data field to inputs or outputs

This requires changes in five places. Example: adding a `"colour"` field to inputs.

**Step 1 — Add to the default data structure in `PatchData.__init__`:**

```python
self.inputs = [{"name": "", "box": "---", "socket": 0,
                "note": "", "location": "", "colour": ""}   # ← add here
               for _ in range(NUM_INPUTS)]
```

**Step 2 — Migrate old save files in `PatchData.from_dict`:**

```python
for ch in raw_inputs:
    ch.setdefault("location", "")
    ch.setdefault("colour", "")          # ← add this
```

**Step 3 — Add a widget in `_make_input_row`:**

```python
colour_var = tk.StringVar(value=d.get("colour", ""))
tk.Entry(frame, textvariable=colour_var, font=FTS,
         bg=BG, fg=YELLOW, insertbackground=YELLOW,
         relief="flat", bd=1, width=10, ...).pack(side="left", ...)
```

**Step 4 — Include the variable in the `row` dict:**

```python
row = {"name": name_var, ..., "colour": colour_var, ...}
```

**Step 5 — Write it back in `_sync_input_data`:**

```python
self.data.inputs[idx]["colour"] = row["colour"].get()
```

Also add a `trace_add` call and update `_refresh_all` to push the value back to the widget when loading.

---

### 9.6 Change the colour scheme

All colour values are named constants at the top of the file. Change the hex strings:

```python
BG     = "#1e1e2e"   # e.g. switch to Catppuccin Mocha base
ACCENT = "#89b4fa"   # blue
GREEN  = "#a6e3a1"   # green
```

If you want different colours for specific boxes, edit `BOX_COLORS`:

```python
BOX_COLORS = [
    "#89b4fa",   # blue
    "#a6e3a1",   # green
    ...
]
```

---

### 9.7 Change fonts

Font constants are near the top. They are tuples of `(family, size)` or `(family, size, style)`:

```python
FT   = ("Helvetica", 11)              # switch away from Courier New
FTB  = ("Helvetica", 11, "bold")
FTTL = ("Helvetica", 18, "bold")
```

Any system font can be used. Stick to monospaced fonts (`Courier New`, `Consolas`, `Menlo`) if you want the text export columns to align.

---

### 9.8 Resize the window

In `App.__init__`:

```python
self.geometry("1400x880")   # width x height in pixels
```

Change either or both numbers. The app is responsive — scrollable areas will expand to fill.

---

### 9.9 Add a new tab

1. Create the frame in `_build_ui`:

```python
self._tab_myview = tk.Frame(self._nb, bg=BG)
self._nb.add(self._tab_myview, text="  MY VIEW  ")
```

2. Call a build method:

```python
self._build_myview_tab()
```

3. Write the method:

```python
def _build_myview_tab(self):
    tab = self._tab_myview
    tk.Label(tab, text="Hello from my tab", font=FTH, bg=BG, fg=ACCENT).pack(pady=20)
```

4. If the tab needs to refresh when switched to, add a case in `_on_tab_change`:

```python
def _on_tab_change(self, _):
    idx = self._nb.index(self._nb.select())
    if idx == 2: self._refresh_box_patch_labels()
    elif idx == 3: self._refresh_labels()
    elif idx == 4: self._refresh_myview()    # ← new tab is index 4
```

---

### 9.10 Add an import from CSV feature

Add a button to the inputs toolbar in `_build_inputs_tab`:

```python
tk.Button(bar, text=" Import CSV", command=self._import_csv, ...).pack(side="right", ...)
```

Then write the method:

```python
def _import_csv(self):
    import csv
    path = filedialog.askopenfilename(
        filetypes=[("CSV", "*.csv")], title="Import CSV")
    if not path: return
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= NUM_INPUTS: break
            self.data.inputs[i]["name"]     = row.get("name", "")
            self.data.inputs[i]["location"] = row.get("location", "")
            self.data.inputs[i]["note"]     = row.get("note", "")
    self.data.rebuild_assigned_from_data()
    self._refresh_all()
```

Expected CSV columns: `name`, `location`, `note` (box/socket assignments are not imported this way since they depend on socket mode state).

---

## 10. Troubleshooting Common Issues

| Symptom | Likely cause | Fix |
|---|---|---|
| Socket dropdown shows no options | Socket modes not set to the right direction, or all sockets already assigned | Check Stage Boxes tab — make sure at least one socket is set to `IN` (for inputs) or `OUT` (for outputs) |
| Changing a socket clears another channel's socket | Both channels were assigned the same socket in a previous/corrupt save | Click **Load** again or manually clear and re-assign |
| Label View tab is out of date | Tab caches its render until refreshed | Click the `-> Refresh` button on that tab |
| App hangs or freezes on startup | Rare race in `trace_add` callbacks | The `_building` flag should prevent this — check that `self._building = False` is set *after* `_build_ui()` |
| Exported `.txt` file has misaligned columns | Channel names longer than column widths | Increase the `width` format string in `_export_txt`; e.g. change `{ch['name']:<24}` to `{ch['name']:<30}` |
| New field not saving to JSON | Forgot to add to `to_dict` / `from_dict` | `to_dict` calls `{"inputs": self.inputs, ...}` — the inputs list is saved as-is, so as long as `_sync_input_data` writes to `self.data.inputs[i]["your_field"]`, it will appear in the JSON automatically |

---

## 11. Dependency & Environment Notes

The app uses **only the Python standard library**:

- `tkinter` — built into Python on Windows and macOS. On Linux you may need to install it: `sudo apt install python3-tk`
- `json` — standard library
- `csv` — standard library (only needed if you add the CSV import feature)

**Minimum Python version:** 3.6 (uses f-strings and `tk.StringVar.trace_add` which replaced the older `trace` method).

**To run:**

```bash
python stagebox_manager_fixed_6_.py
```

**To package as a standalone executable (optional):**

```bash
pip install pyinstaller
pyinstaller --onefile --windowed stagebox_manager_fixed_6_.py
```

The resulting executable in the `dist/` folder has no Python dependency.
