#!/usr/bin/env python3
"""
KiBot Variant Manager v4 — Windows XP style, red corporate theme
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import yaml, subprocess, threading, os, re, shutil, glob, json, sys, datetime
from pathlib import Path

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

IS_WINDOWS = sys.platform == 'win32'
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".kibot_manager.json")
POPEN_FLAGS = {}
if IS_WINDOWS:
    POPEN_FLAGS['creationflags'] = 0x08000000

# ══════════════════════════════════════════════
#  XP STYLE CONSTANTS
# ══════════════════════════════════════════════

XP = {
    'title_bg': '#C8102E',
    'title_fg': '#FFFFFF',
    'title_shadow': '#8B0000',
    'toolbar_bg': '#D4D0C8',
    'toolbar_border': '#808080',
    'bg': '#D4D0C8',
    'panel_bg': '#ECE9D8',
    'white': '#FFFFFF',
    'black': '#000000',
    'text': '#000000',
    'text2': '#444444',
    'text3': '#808080',
    'btn_face': '#ECE9D8',
    'btn_highlight': '#FFFFFF',
    'btn_shadow': '#808080',
    'btn_dark': '#404040',
    'btn_hover': '#F0EDE4',
    'border_light': '#FFFFFF',
    'border_dark': '#808080',
    'border_darker': '#404040',
    'field_bg': '#FFFFFF',
    'selection': '#C8102E',
    'selection_light': '#F4D4D9',
    'ok': '#008000',
    'err': '#CC0000',
    'warn': '#CC6600',
    'info': '#000080',
    'progress_bg': '#FFFFFF',
    'progress_fill': '#C8102E',
    'progress_chunk': '#E03040',
    'scrollbar': '#C0C0C0',
    'status_bg': '#ECE9D8',
    'status_border': '#808080',
    'terminal_bg': '#000000',
    'terminal_fg': '#C0C0C0',
}

# ══════════════════════════════════════════════
#  S-expression parser & converter (unchanged logic)
# ══════════════════════════════════════════════

class SNode:
    def __init__(self, ntype, name="", value="", children=None):
        self.type = ntype; self.name = name; self.value = value; self.children = children or []

def parse_sexpr(text):
    tokens = _tokenize(text); idx, node = _parse_node(tokens, 0); return node

def _tokenize(text):
    tokens = []; i = 0; n = len(text)
    while i < n:
        c = text[i]
        if c in ' \t\n\r': i += 1; continue
        if c == ';' and i+1 < n and text[i+1] == ';':
            while i < n and text[i] != '\n': i += 1
            continue
        if c == '(': tokens.append(('open', None)); i += 1; continue
        if c == ')': tokens.append(('close', None)); i += 1; continue
        if c == '"':
            i += 1; s = []
            while i < n:
                if text[i] == '\\' and i+1 < n:
                    nc = text[i+1]; s.append({'n':'\n','r':'\r','t':'\t','\\':'\\','"':'"'}.get(nc, '\\'+nc)); i += 2
                elif text[i] == '"': i += 1; break
                else: s.append(text[i]); i += 1
            tokens.append(('string', ''.join(s))); continue
        s = []
        while i < n and text[i] not in '() \t\n\r"': s.append(text[i]); i += 1
        tokens.append(('atom', ''.join(s)))
    return tokens

def _parse_node(tokens, idx):
    if idx >= len(tokens): return idx, None
    tt, tv = tokens[idx]
    if tt == 'open':
        idx += 1; children = []; name = None
        while idx < len(tokens):
            if tokens[idx][0] == 'close': idx += 1; break
            idx, child = _parse_node(tokens, idx)
            if child is None: break
            if name is None and child.type in ('atom','string'): name = child.value
            else: children.append(child)
        return idx, SNode('list', name=name or '', children=children)
    if tt == 'atom': return idx+1, SNode('atom', value=tv)
    if tt == 'string': return idx+1, SNode('string', value=tv)
    return idx+1, None

def _escape(s): return s.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n').replace('\r','\\r').replace('\t','\\t')

def _is_compact(node):
    if not node.children: return True
    if all(c.type in ('atom','string') for c in node.children) and len(node.children) <= 6: return True
    compact = {'version','generator','generator_version','uuid','paper','at','size','xy','center',
               'radius','width','type','diameter','color','offset','length','number','name',
               'justify','hide','page','comment','path','reference','unit','in_bom','on_board',
               'exclude_from_sim','dnp','exclude_from_board','fields_autoplaced','embedded_fonts','mirror'}
    if node.name in compact: return True
    if node.name == 'pts' and len(node.children) <= 4 and all(c.type=='list' and c.name=='xy' for c in node.children): return True
    return False

def serialize(node, depth=0):
    if node is None: return ''
    if node.type == 'atom': return node.value
    if node.type == 'string': return f'"{_escape(node.value)}"'
    indent = '\t'*depth; inner = '\t'*(depth+1)
    if _is_compact(node):
        parts = ' '.join(serialize(c, depth+1) for c in node.children)
        return f'({node.name} {parts})' if parts else f'({node.name})'
    inline = []; rest_start = 0
    for i, c in enumerate(node.children):
        if c.type in ('atom','string'): inline.append(c); rest_start = i+1
        else: break
    hdr = f'({node.name}'
    if len(inline) > 6: hdr += '\n' + ''.join(inner+serialize(c,depth+1)+'\n' for c in inline)
    elif inline: hdr += ' ' + ' '.join(serialize(c,depth+1) for c in inline) + '\n'
    else: hdr += '\n'
    for c in node.children[rest_start:]: hdr += inner + serialize(c, depth+1) + '\n'
    hdr += indent + ')'; return hdr

def find_child(n, name):
    if not n or n.type != 'list': return None
    for c in n.children:
        if c.type == 'list' and c.name == name: return c
    return None
def find_all(n, name): return [c for c in n.children if c.type=='list' and c.name==name] if n and n.type=='list' else []
def remove_all(n, name):
    if not n or n.type != 'list': return 0
    b = len(n.children); n.children = [c for c in n.children if not(c.type=='list' and c.name==name)]; return b-len(n.children)
def set_value(n, cname, val):
    c = find_child(n, cname)
    if not c: return False
    if not c.children: c.children.append(SNode('atom', value=str(val)))
    else: c.children[0].value = str(val)
    return True

def convert_sch_10to9(root, log):
    set_value(root, 'version', '20250114'); set_value(root, 'generator_version', '9.0')
    log.append("Header -> v9"); _walk_sch(root, log, False)
    n = remove_all(root, 'group')
    if n: log.append(f"Removed {n} group(s)")

def _walk_sch(node, log, in_lib):
    if not node or node.type != 'list': return
    is_lib = node.name == 'lib_symbols'; child_in_lib = in_lib or is_lib
    if node.name == 'symbol' and any(c.type=='list' and c.name=='in_pos_files' for c in node.children):
        remove_all(node, 'in_pos_files'); remove_all(node, 'duplicate_pin_numbers_are_jumpers')
    if node.name == 'property':
        remove_all(node, 'show_name'); remove_all(node, 'do_not_autoplace')
        idx = next((i for i,c in enumerate(node.children) if c.type=='list' and c.name=='hide'), -1)
        if idx >= 0:
            hv = node.children[idx].children[0].value if node.children[idx].children else 'yes'
            node.children.pop(idx)
            if hv == 'yes':
                eff = find_child(node, 'effects')
                if eff: eff.children.append(SNode('list', name='hide', children=[SNode('atom', value='yes')]))
    if node.name == 'power':
        for i, c in enumerate(node.children):
            if c.type == 'atom' and c.value == 'global': node.children.pop(i); break
    if node.name == 'symbol':
        remove_all(node, 'body_styles')
        if not is_lib and any(c.type=='list' and c.name=='lib_id' for c in node.children): remove_all(node, 'body_style')
    if node.name == 'name' and child_in_lib and node.children:
        if node.children[0].value == '': node.children[0].value = '~'
    if node.name == 'path': remove_all(node, 'variant')
    for c in node.children: _walk_sch(c, log, child_in_lib)

def convert_pcb_10to9(root, log):
    set_value(root, 'version', '20241229'); set_value(root, 'generator_version', '9.0')
    log.append("PCB Header -> v9")
    setup = find_child(root, 'setup')
    if setup:
        tent = find_child(setup, 'tenting')
        if tent:
            f = find_child(tent,'front'); b = find_child(tent,'back'); ch = []
            if f and (not f.children or f.children[0].value=='yes'): ch.append(SNode('atom',value='front'))
            if b and (not b.children or b.children[0].value=='yes'): ch.append(SNode('atom',value='back'))
            tent.children = ch
        for a in ('covering','plugging','capping','filling'): remove_all(setup, a)
        pp = find_child(setup, 'pcbplotparams')
        if pp:
            for pn,pv in [('hpglpennumber','1'),('hpglpenspeed','20'),('hpglpendiameter','15.000000'),('plotinvisibletext','no')]:
                if not find_child(pp, pn): pp.children.append(SNode('list', name=pn, children=[SNode('atom', value=pv)]))
    nets = _collect_nets(root)
    if nets:
        si = next((i for i,c in enumerate(root.children) if c.type=='list' and c.name=='setup'), -1)
        ins = si+1 if si >= 0 else len(root.children)
        for name, idx in sorted(nets.items(), key=lambda x: x[1]):
            root.children.insert(ins, SNode('list', name='net', children=[SNode('atom',value=str(idx)), SNode('string',value=name)])); ins += 1
    _walk_pcb(root, nets, log)

def _collect_nets(root):
    ns = set()
    def w(n):
        if not n or n.type != 'list': return
        if n.name in ('segment','arc','via','zone','pad'):
            nc = find_child(n,'net')
            if nc and nc.children:
                v = nc.children[0]
                if v.type=='string' or (v.type=='atom' and not v.value.lstrip('-').isdigit()): ns.add(v.value)
        for c in n.children: w(c)
    w(root); m = {'':0}
    for i, name in enumerate(sorted(ns-{''}), 1): m[name] = i
    return m

def _walk_pcb(node, nm, log):
    if not node or node.type != 'list': return
    if node.name in ('segment','arc','via'):
        nc = find_child(node,'net')
        if nc and nc.children:
            v = nc.children[0]
            if v.type=='string' or (v.type=='atom' and not v.value.lstrip('-').isdigit()):
                nid = nm.get(v.value)
                if nid is not None: nc.children = [SNode('atom',value=str(nid))]
    if node.name == 'pad':
        nc = find_child(node,'net')
        if nc and nc.children:
            v = nc.children[0]
            if v.type=='string' or (v.type=='atom' and not v.value.lstrip('-').isdigit()):
                nid = nm.get(v.value)
                if nid is not None: nc.children = [SNode('atom',value=str(nid)), SNode('string',value=v.value)]
    if node.name == 'zone':
        nc = find_child(node,'net')
        if nc and nc.children:
            v = nc.children[0]
            if v.type=='string' or (v.type=='atom' and not v.value.lstrip('-').isdigit()):
                nid = nm.get(v.value)
                if nid is not None:
                    nc.children = [SNode('atom',value=str(nid))]
                    if not find_child(node,'net_name'):
                        idx = next((i for i,c in enumerate(node.children) if c is nc),0)+1
                        node.children.insert(idx, SNode('list',name='net_name',children=[SNode('string',value=v.value)]))
        fl = find_child(node,'fill')
        if fl: remove_all(fl,'island_removal_mode')
        if not find_child(node,'filled_areas_thickness'):
            fi = next((i for i,c in enumerate(node.children) if c.type=='list' and c.name=='fill'),-1)
            node.children.insert(fi+1 if fi>=0 else len(node.children), SNode('list',name='filled_areas_thickness',children=[SNode('atom',value='no')]))
    if node.name == 'via':
        for a in ('capping','covering','plugging','filling'): remove_all(node, a)
    if node.name == 'footprint':
        for a in ('units','duplicate_pad_numbers_are_jumpers','point','component_classes'): remove_all(node, a)
        for prop in find_all(node,'property'):
            if not prop.children: continue
            pn = prop.children[0].value
            if pn in ('Datasheet','Description'):
                if not any(c.type=='list' and c.name=='unlocked' for c in prop.children):
                    li = next((i for i,c in enumerate(prop.children) if c.type=='list' and c.name=='layer'), len(prop.children))
                    prop.children.insert(li, SNode('list',name='unlocked',children=[SNode('atom',value='yes')]))
                eff = find_child(prop,'effects')
                if eff:
                    font = find_child(eff,'font')
                    if font and not any(c.type=='list' and c.name=='thickness' for c in font.children):
                        font.children.append(SNode('list',name='thickness',children=[SNode('atom',value='0.15')]))
    for c in node.children: _walk_pcb(c, nm, log)

# ══════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════

def detect_kicad_version(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f: head = f.read(2000)
        m = re.search(r'\(version\s+(\d+)\)', head)
        if not m: return None, "unknown"
        ver = int(m.group(1))
        if filepath.endswith('.kicad_sch'):
            if ver > 20250114: return ver, "KiCad 10"
            if ver > 20231120: return ver, "KiCad 9"
            return ver, "KiCad 7/8"
        if filepath.endswith('.kicad_pcb'):
            if ver > 20241229: return ver, "KiCad 10"
            if ver > 20240108: return ver, "KiCad 9"
            return ver, "KiCad 7/8"
        return ver, "unknown"
    except: return None, "error"

def get_project_name(d):
    schs = glob.glob(os.path.join(d, '*.kicad_sch'))
    if not schs: return None
    for f in schs:
        nm = Path(f).stem
        if '_sheet' not in nm and '-sheet' not in nm and '_sub' not in nm: return nm
    return Path(schs[0]).stem

def generate_kicad_pro(name, out_dir):
    pro = {"meta":{"filename":f"{name}.kicad_pro","version":1},"project":{"meta":{"version":3},"schematic":{"meta":{"version":1}},"boards":[],"text_variables":{}}}
    p = os.path.join(out_dir, f"{name}.kicad_pro")
    with open(p, 'w', encoding='utf-8') as f: json.dump(pro, f, indent=2)
    return p

def convert_file_10to9(filepath, dest, log_cb):
    bn = os.path.basename(filepath)
    with open(filepath, 'r', encoding='utf-8') as f: content = f.read()
    root = parse_sexpr(content)
    if root is None: log_cb(f"  ERROR: parse failed"); return False
    cl = []
    if filepath.endswith('.kicad_sch'): convert_sch_10to9(root, cl)
    elif filepath.endswith('.kicad_pcb'): convert_pcb_10to9(root, cl)
    else: return False
    out = serialize(root) + '\n'
    with open(os.path.join(dest, bn), 'w', encoding='utf-8') as f: f.write(out)
    for l in cl: log_cb(f"    {l}")
    log_cb(f"  OK: {bn}"); return True

def wsl_path(win_path):
    if not IS_WINDOWS: return win_path
    try: return subprocess.check_output(['wsl','wslpath','-u',win_path], text=True, encoding='utf-8', **POPEN_FLAGS).strip()
    except: return win_path

def check_requirements():
    results = []
    if not IS_WINDOWS:
        results.append(("WSL", True, "Linux nativo"))
        try:
            v = subprocess.check_output(['kibot','--version'], text=True, stderr=subprocess.STDOUT).strip()
            results.append(("KiBot", True, v))
        except: results.append(("KiBot", False, "No encontrado"))
        try:
            subprocess.check_output(['python3','-c','import pcbnew'], text=True, stderr=subprocess.STDOUT)
            results.append(("KiCad", True, "OK"))
        except: results.append(("KiCad", False, "No encontrado"))
        return results
    try:
        subprocess.check_output(['wsl','echo','ok'], text=True, **POPEN_FLAGS)
        results.append(("WSL", True, "OK"))
    except:
        results.append(("WSL", False, "No instalado")); return results
    try:
        v = subprocess.check_output(['wsl','bash','-lc','kibot --version'], text=True, encoding='utf-8', **POPEN_FLAGS).strip()
        results.append(("KiBot", True, v))
    except: results.append(("KiBot", False, "No instalado en WSL"))
    try:
        subprocess.check_output(['wsl','bash','-lc','python3 -c "import pcbnew"'], text=True, encoding='utf-8', **POPEN_FLAGS)
        results.append(("KiCad", True, "OK"))
    except: results.append(("KiCad", False, "No instalado en WSL"))
    return results

def load_config():
    try:
        with open(CONFIG_FILE,'r') as f: return json.load(f)
    except: return {}

def save_config(c):
    try:
        with open(CONFIG_FILE,'w') as f: json.dump(c, f)
    except: pass

def validate_yaml(data):
    errs = []
    if not isinstance(data, dict): return False, ["YAML no es un diccionario"]
    if 'variants' not in data: return False, ["Falta clave 'variants'"]
    v = data['variants']
    if not isinstance(v, list): return False, ["'variants' debe ser una lista"]
    if len(v) == 0: return False, ["Lista 'variants' vacia"]
    for i, x in enumerate(v):
        if not isinstance(x, dict): errs.append(f"Variante {i+1}: no es diccionario")
        elif 'name' not in x: errs.append(f"Variante {i+1}: falta 'name'")
    return len(errs)==0, errs

# ══════════════════════════════════════════════
#  XP-STYLE WIDGETS
# ══════════════════════════════════════════════

class XPButton(tk.Button):
    """Styled button like Windows XP."""
    def __init__(self, parent, text="", command=None, width=120, height=28, **kw):
        self._w_px = width
        self._h_px = height
        super().__init__(parent, text=text, command=command,
                         font=("Tahoma", 9), relief='raised', bd=2,
                         bg=XP['btn_face'], fg=XP['text'],
                         activebackground='#D0CEC6', activeforeground=XP['text'],
                         cursor='hand2', padx=8, pady=4)
        self.bind('<Enter>', lambda e: self.config(bg=XP['btn_hover']) if self['state'] != 'disabled' else None)
        self.bind('<Leave>', lambda e: self.config(bg=XP['btn_face']) if self['state'] != 'disabled' else None)

    def set_state(self, enabled):
        self.config(state='normal' if enabled else 'disabled',
                    bg=XP['btn_face'] if enabled else '#C0C0C0',
                    cursor='hand2' if enabled else 'arrow')

    def set_text(self, t):
        self.config(text=t)


class XPProgress(tk.Frame):
    """Chunked progress bar like Windows XP."""
    def __init__(self, parent, width=300, height=22, **kw):
        super().__init__(parent, height=height, bg=XP['bg'])
        self._canvas = tk.Canvas(self, width=width, height=height,
                                  highlightthickness=0, bg=XP['bg'])
        self._canvas.pack(fill='x', expand=True)
        self._h = height
        self._value = 0
        self.bind('<Configure>', lambda e: self._draw())

    def _draw(self):
        c = self._canvas
        c.delete('all')
        w = c.winfo_width() or 300
        h = self._h
        c.create_rectangle(0, 0, w-1, h-1, outline=XP['btn_shadow'])
        c.create_rectangle(1, 1, w-2, h-2, outline=XP['btn_dark'])
        c.create_rectangle(2, 2, w-3, h-3, fill=XP['progress_bg'], outline='')
        if self._value > 0:
            fill_w = int((w - 6) * min(self._value, 1.0))
            x = 3
            while x < 3 + fill_w:
                cw = min(8, 3 + fill_w - x)
                c.create_rectangle(x, 3, x+cw, h-4, fill=XP['progress_fill'], outline='')
                c.create_rectangle(x, 3, x+cw, 6, fill=XP['progress_chunk'], outline='')
                x += 10

    def set_value(self, v):
        self._value = v; self._draw()


# ══════════════════════════════════════════════
#  GUI
# ══════════════════════════════════════════════

class KiBotGUI(TkinterDnD.Tk if HAS_DND else tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("KiBot Variant Manager")
        self.geometry("1050x720")
        self.minsize(860, 560)
        self.configure(bg=XP['bg'])

        self.variants = []
        self.yaml_path = None
        self.project_dir = None
        self.kicad10_detected = False
        self.kicad10_files = []
        self.current_proc = None
        self.requirements_ok = False
        self.execution_history = []
        self.variant_buttons = {}
        self.detected_version = ""
        self._yaml_data = {}

        self._build_ui()
        self._check_startup()

    def _build_ui(self):
        # ═══ TITLE BAR ═══
        title = tk.Frame(self, bg=XP['title_bg'], height=36)
        title.pack(fill='x')
        title.pack_propagate(False)
        # shadow text
        tk.Label(title, text=" KiBot Variant Manager", fg=XP['title_shadow'],
                 bg=XP['title_bg'], font=("Tahoma", 12, "bold")).place(x=7, y=7)
        tk.Label(title, text=" KiBot Variant Manager", fg=XP['title_fg'],
                 bg=XP['title_bg'], font=("Tahoma", 12, "bold")).place(x=6, y=6)

        # ═══ TOOLBAR ═══
        toolbar = tk.Frame(self, bg=XP['toolbar_bg'], height=38)
        toolbar.pack(fill='x')
        toolbar.pack_propagate(False)
        # separator
        tk.Frame(toolbar, bg=XP['btn_shadow'], height=1).pack(fill='x', side='top')

        tbtn_frame = tk.Frame(toolbar, bg=XP['toolbar_bg'])
        tbtn_frame.pack(fill='x', padx=4, pady=3)

        self.btn_load = XPButton(tbtn_frame, text="Cargar YAML", command=self._load_yaml, width=110, height=26)
        self.btn_load.pack(side='left', padx=2)
        self.btn_clear = XPButton(tbtn_frame, text="Limpiar", command=self._clear_all, width=80, height=26)
        self.btn_clear.pack(side='left', padx=2)
        self.btn_cancel = XPButton(tbtn_frame, text="Cancelar", command=self._cancel_process, width=80, height=26)
        self.btn_cancel.pack(side='left', padx=2)
        self.btn_cancel.set_state(False)

        tk.Frame(tbtn_frame, bg=XP['btn_shadow'], width=1).pack(side='left', fill='y', padx=4)
        self.btn_open_output = XPButton(tbtn_frame, text="Abrir salida", command=self._open_output_folder, width=95, height=26)
        self.btn_open_output.pack(side='left', padx=2)
        self.btn_open_output.set_state(False)
        self.btn_export_log = XPButton(tbtn_frame, text="Exportar log", command=self._export_log, width=90, height=26)
        self.btn_export_log.pack(side='left', padx=2)
        self.btn_export_log.set_state(False)

        tk.Frame(self, bg=XP['btn_shadow'], height=1).pack(fill='x')

        # ═══ DROP ZONE ═══
        self.drop_frame = tk.Frame(self, bg=XP['bg'])
        self.drop_frame.pack(fill='both', expand=True)
        self._build_drop_zone()

        # ═══ MAIN FRAME ═══
        self.main_frame = tk.Frame(self, bg=XP['bg'])

        # ── LEFT SIDEBAR ──
        sidebar = tk.Frame(self.main_frame, bg=XP['panel_bg'], width=220)
        sidebar.pack(side='left', fill='y', padx=(4,0), pady=4)
        sidebar.pack_propagate(False)

        # sidebar border
        tk.Frame(sidebar, bg=XP['btn_shadow'], width=1).pack(side='right', fill='y')

        # sidebar header
        sh = tk.Frame(sidebar, bg=XP['title_bg'], height=24)
        sh.pack(fill='x')
        sh.pack_propagate(False)
        tk.Label(sh, text="  Variantes", fg='white', bg=XP['title_bg'],
                 font=("Tahoma", 9, "bold")).pack(side='left')

        self.btn_frame = tk.Frame(sidebar, bg=XP['panel_bg'])
        self.btn_frame.pack(fill='both', expand=True, padx=4, pady=4)

        self.convert_btn = XPButton(sidebar, text="!! Convertir KiCad 10->9",
                                     command=self._convert_dialog, width=200, height=30)

        # ── RIGHT AREA ──
        right = tk.Frame(self.main_frame, bg=XP['bg'])
        right.pack(side='left', fill='both', expand=True, padx=4, pady=4)

        # ── PROJECT CARD ──
        self.project_card = tk.LabelFrame(right, text="  Proyecto  ", bg=XP['panel_bg'],
                                           fg=XP['info'], font=("Tahoma", 9, "bold"),
                                           relief='groove', bd=2, padx=8, pady=4)
        self.card_vars = {}
        for _key, _lbl in [('nombre', 'PCB'), ('variantes', 'Variantes'), ('version', 'Version KiCad'),
                             ('fecha', 'Fecha YAML'), ('outputs', 'Outputs'), ('ruta', 'Ruta')]:
            _row = tk.Frame(self.project_card, bg=XP['panel_bg'])
            _row.pack(fill='x', pady=0)
            tk.Label(_row, text=f"{_lbl}:", bg=XP['panel_bg'], fg=XP['text2'],
                     font=("Tahoma", 8, "bold"), width=12, anchor='w').pack(side='left')
            _v = tk.StringVar()
            self.card_vars[_key] = _v
            tk.Label(_row, textvariable=_v, bg=XP['panel_bg'], fg=XP['text'],
                     font=("Tahoma", 8), anchor='w').pack(side='left', fill='x', expand=True)

        # ── STATUS BOX (groupbox style) ──
        self.status_outer = tk.Frame(right, bg=XP['bg'])
        self.status_outer.pack(fill='x', pady=(0,4))
        status_outer = self.status_outer

        # groupbox border
        gb = tk.LabelFrame(status_outer, text="  Estado  ", bg=XP['panel_bg'],
                           fg=XP['info'], font=("Tahoma", 9, "bold"),
                           relief='groove', bd=2, padx=8, pady=4)
        gb.pack(fill='x')

        self.steps_frame = tk.Frame(gb, bg=XP['panel_bg'])
        self.steps_frame.pack(fill='x')

        self.step_labels = {}
        for sid, stxt in [('yaml','YAML cargado'), ('version','Version compatible'), ('ready','Listo para generar')]:
            row = tk.Frame(self.steps_frame, bg=XP['panel_bg'])
            row.pack(fill='x', pady=1)
            ind = tk.Label(row, text="[ -- ]", bg=XP['panel_bg'], fg=XP['text3'],
                           font=("Tahoma", 8, "bold"), width=8, anchor='w')
            ind.pack(side='left')
            lbl = tk.Label(row, text=stxt, bg=XP['panel_bg'], fg=XP['text3'],
                           font=("Tahoma", 9), anchor='w')
            lbl.pack(side='left')
            self.step_labels[sid] = (ind, lbl)

        # ── PROGRESS BAR ──
        prog_frame = tk.LabelFrame(right, text="  Progreso  ", bg=XP['panel_bg'],
                                    fg=XP['info'], font=("Tahoma", 9, "bold"),
                                    relief='groove', bd=2, padx=8, pady=6)
        prog_frame.pack(fill='x', pady=(0,4))

        self.progress = XPProgress(prog_frame, width=600, height=22)
        self.progress.pack(fill='x')

        # ── HISTORIAL ──
        hist_gb = tk.LabelFrame(right, text="  Historial de ejecuciones  ", bg=XP['panel_bg'],
                                 fg=XP['info'], font=("Tahoma", 9, "bold"),
                                 relief='groove', bd=2, padx=4, pady=4)
        hist_gb.pack(fill='x', pady=(0,4))
        self.hist_list = tk.Listbox(hist_gb, bg=XP['white'], fg=XP['text'],
                                     font=("Lucida Console", 8) if IS_WINDOWS else ("Consolas", 8),
                                     height=4, relief='sunken', bd=2,
                                     selectbackground=XP['selection'], selectforeground='white')
        self.hist_list.pack(fill='x')

        # ── TERMINAL ──
        term_gb = tk.LabelFrame(right, text="  Terminal  ", bg=XP['bg'],
                                 fg=XP['info'], font=("Tahoma", 9, "bold"),
                                 relief='groove', bd=2, padx=4, pady=4)
        term_gb.pack(fill='both', expand=True)

        # sunken frame for terminal
        term_border = tk.Frame(term_gb, bg=XP['btn_shadow'], bd=0)
        term_border.pack(fill='both', expand=True)

        self.log = scrolledtext.ScrolledText(term_border, bg=XP['terminal_bg'], fg=XP['terminal_fg'],
                                              font=("Lucida Console", 9) if IS_WINDOWS else ("Consolas", 9),
                                              wrap='word', insertbackground='white',
                                              relief='sunken', bd=2)
        self.log.pack(fill='both', expand=True, padx=1, pady=1)
        self.log.tag_config('err', foreground='#FF6B6B')
        self.log.tag_config('warn', foreground='#FFB347')
        self.log.tag_config('ok', foreground='#90EE90')
        self.log.tag_config('info', foreground='#87CEEB')
        self.log.tag_config('dim', foreground='#666666')

        # ═══ STATUS BAR ═══
        sb_frame = tk.Frame(self, bg=XP['status_bg'], height=24)
        sb_frame.pack(side='bottom', fill='x')
        sb_frame.pack_propagate(False)
        # top border
        tk.Frame(sb_frame, bg=XP['btn_shadow'], height=1).pack(fill='x', side='top')
        # grip
        tk.Frame(sb_frame, bg=XP['btn_shadow'], width=2).pack(side='left', fill='y', padx=(2,4))

        self.status_var = tk.StringVar(value="Iniciando...")
        tk.Label(sb_frame, textvariable=self.status_var, bg=XP['status_bg'], fg=XP['text2'],
                 font=("Tahoma", 8), anchor='w').pack(side='left', fill='x', expand=True, padx=4)

    def _build_drop_zone(self):
        # XP explorer-like window area
        outer = tk.Frame(self.drop_frame, bg=XP['panel_bg'], relief='sunken', bd=2)
        outer.pack(expand=True, fill='both', padx=20, pady=20)

        inner = tk.Frame(outer, bg=XP['white'])
        inner.pack(expand=True, fill='both', padx=2, pady=2)

        center = tk.Frame(inner, bg=XP['white'])
        center.place(relx=0.5, rely=0.4, anchor='center')

        # folder icon style
        tk.Label(center, text="[  ]", font=("Tahoma", 48, "bold"),
                 bg=XP['white'], fg='#FFD700').pack()
        tk.Label(center, text="Arrastre su archivo YAML aqui",
                 font=("Tahoma", 13, "bold"), bg=XP['white'], fg=XP['text']).pack(pady=(8,2))
        tk.Label(center, text="o use el boton 'Cargar YAML' de la barra de herramientas",
                 font=("Tahoma", 9), bg=XP['white'], fg=XP['text3']).pack()

        if HAS_DND:
            inner.drop_target_register(DND_FILES)
            inner.dnd_bind('<<DropEnter>>', lambda e: inner.configure(bg=XP['selection_light']))
            inner.dnd_bind('<<DropLeave>>', lambda e: inner.configure(bg=XP['white']))
            inner.dnd_bind('<<Drop>>', self._on_drop)
            tk.Label(center, text="[Drag & Drop activo]", font=("Tahoma", 8, "bold"),
                     bg=XP['white'], fg=XP['ok']).pack(pady=(10,0))
        else:
            tk.Label(center, text="Instale tkinterdnd2 para arrastrar y soltar",
                     font=("Tahoma", 8), bg=XP['white'], fg=XP['warn']).pack(pady=(10,0))

        # Requirements at bottom
        self.req_frame = tk.LabelFrame(inner, text="  Requisitos del sistema  ",
                                        bg=XP['white'], fg=XP['info'],
                                        font=("Tahoma", 8, "bold"), relief='groove', bd=2)
        self.req_frame.pack(side='bottom', fill='x', padx=16, pady=12)

    # ── STARTUP ──

    def _check_startup(self):
        self.status_var.set("Comprobando requisitos...")
        self.update_idletasks()
        reqs = check_requirements()
        self.requirements_ok = all(ok for _, ok, _ in reqs)
        for w in self.req_frame.winfo_children(): w.destroy()
        for name, ok, detail in reqs:
            row = tk.Frame(self.req_frame, bg=XP['white'])
            row.pack(fill='x', pady=1, padx=4)
            icon = "[OK]" if ok else "[!!]"
            color = XP['ok'] if ok else XP['err']
            tk.Label(row, text=icon, bg=XP['white'], fg=color, font=("Tahoma", 8, "bold"),
                     width=5, anchor='w').pack(side='left')
            tk.Label(row, text=f"{name}: {detail}", bg=XP['white'], fg=XP['text2'],
                     font=("Tahoma", 8), anchor='w').pack(side='left')
        self.status_var.set("Listo" if self.requirements_ok else "Faltan requisitos del sistema")

    # ── STEP INDICATORS ──

    def _set_step(self, sid, state):
        ind, lbl = self.step_labels[sid]
        m = {'ok':('[OK]', XP['ok']), 'error':('[!!]', XP['err']),
             'running':('[>>]', XP['info']), 'pending':('[ -- ]', XP['text3'])}
        txt, col = m.get(state, ('[ -- ]', XP['text3']))
        ind.config(text=txt, fg=col); lbl.config(fg=col)

    # ── EVENTS ──

    def _on_drop(self, event):
        raw = event.data
        paths = re.findall(r'\{([^}]+)\}', raw) if '{' in raw else raw.split()
        for p in paths:
            p = p.strip()
            if p.lower().endswith(('.yaml','.yml')) and os.path.isfile(p):
                self._process_yaml(p); return
        messagebox.showwarning("Archivo", "Suelte un archivo .yaml o .yml")

    def _log(self, msg, tag=None):
        self.log.insert('end', msg + '\n', tag or ''); self.log.see('end')

    def _clear_all(self):
        self.variants = []; self.yaml_path = None; self.project_dir = None
        self.kicad10_detected = False; self.kicad10_files = []
        self.variant_buttons = {}; self._yaml_data = {}
        for w in self.btn_frame.winfo_children(): w.destroy()
        self.convert_btn.pack_forget()
        self.log.delete('1.0', 'end')
        self.hist_list.delete(0, 'end')
        self.project_card.pack_forget()
        for s in self.step_labels: self._set_step(s, 'pending')
        self.progress.set_value(0)
        self.btn_open_output.set_state(False)
        self.btn_export_log.set_state(False)
        self.main_frame.pack_forget()
        self.drop_frame.pack(fill='both', expand=True)
        self.status_var.set("Listo")

    def _load_yaml(self):
        cfg = load_config()
        ini = os.path.dirname(cfg.get('last_yaml','')) or None
        path = filedialog.askopenfilename(title="Seleccionar YAML KiBot",
                                           filetypes=[("YAML","*.yaml *.yml"),("Todos","*.*")],
                                           initialdir=ini)
        if path: self._process_yaml(path)

    def _process_yaml(self, path):
        if not self.requirements_ok:
            messagebox.showerror("Requisitos", "Faltan requisitos.\nRevise WSL, KiCad y KiBot."); return
        self.yaml_path = path; self.project_dir = os.path.dirname(path)
        save_config({'last_yaml': path})
        try:
            with open(path, 'r', encoding='utf-8') as f: data = yaml.safe_load(f)
        except Exception as e:
            messagebox.showerror("Error YAML", str(e)); return
        ok, errs = validate_yaml(data)
        if not ok:
            self._set_step('yaml','error')
            messagebox.showerror("YAML invalido", "\n".join(errs)); return
        self.variants = data['variants']
        self._yaml_data = data
        self.drop_frame.pack_forget(); self.main_frame.pack(fill='both', expand=True)
        self.log.delete('1.0','end')
        self._log(f"YAML: {os.path.basename(path)}", 'info')
        self._log(f"Ruta: {self.project_dir}", 'dim')
        self._log(f"Variantes: {len(self.variants)}", 'info')
        self._log("", None)
        self._set_step('yaml','ok')
        self.status_var.set(f"{os.path.basename(self.project_dir)} | {len(self.variants)} variantes")
        self.btn_open_output.set_state(True)
        self.btn_export_log.set_state(True)
        self.variant_buttons = {}
        for w in self.btn_frame.winfo_children(): w.destroy()
        for var in self.variants:
            nm = var.get('name','???'); cm = var.get('comment','')
            btn = XPButton(self.btn_frame, text=nm, command=lambda v=var: self._run_variant(v),
                           width=200, height=26)
            btn.pack(fill='x', pady=2)
            self.variant_buttons[nm] = btn
            if cm:
                tk.Label(self.btn_frame, text=f"  {cm}", bg=XP['panel_bg'], fg=XP['text3'],
                         font=("Tahoma", 7), anchor='w').pack(fill='x')
        self._check_versions()
        self._update_project_card()

    def _check_versions(self):
        self.kicad10_detected = False; self.kicad10_files = []; self.detected_version = ""
        if not self.project_dir: return
        files = glob.glob(os.path.join(self.project_dir,'*.kicad_sch')) + \
                glob.glob(os.path.join(self.project_dir,'*.kicad_pcb'))
        self._log("Comprobando versiones...", 'dim')
        for fp in files:
            ver, label = detect_kicad_version(fp)
            self.detected_version = label
            tag = 'ok' if label != "KiCad 10" else 'err'
            self._log(f"  {os.path.basename(fp)}: {label}", tag)
            if label == "KiCad 10":
                self.kicad10_detected = True; self.kicad10_files.append(fp)
        if self.kicad10_detected:
            self._set_step('version','error'); self._set_step('ready','pending')
            self._log("\n!! KiCad 10 detectado. Convirtiendo automaticamente...", 'warn')
            self.status_var.set("Convirtiendo KiCad 10 -> 9...")
            self.update_idletasks()
            ok = self._auto_convert()
            if ok == len(self.kicad10_files):
                self.kicad10_detected = False; self.kicad10_files = []
                self.detected_version = "KiCad 9 (convertido)"
                self._set_step('version','ok'); self._set_step('ready','ok')
                self.convert_btn.pack_forget()
                for w in self.btn_frame.winfo_children():
                    if isinstance(w, XPButton): w.set_state(True)
                self.status_var.set(f"Convertido a v9 | {len(self.variants)} variantes")
            else:
                self._log(f"!! Algunos archivos fallaron. Use 'Convertir' manual.\n", 'err')
                self.convert_btn.pack(fill='x', padx=4, pady=(4,8))
                for w in self.btn_frame.winfo_children():
                    if isinstance(w, XPButton): w.set_state(False)
                self.status_var.set("Conversion parcial - revision necesaria")
        else:
            self._set_step('version','ok'); self._set_step('ready','ok')
            self.convert_btn.pack_forget()
            self._log("Version compatible.\n", 'ok')
            for w in self.btn_frame.winfo_children():
                if isinstance(w, XPButton): w.set_state(True)

    # ── CONVERSION ──

    def _auto_convert(self):
        yaml_name = Path(self.yaml_path).stem
        backup_dir = os.path.join(self.project_dir, f"{yaml_name}_v10")
        pn = get_project_name(self.project_dir) or "proyecto"
        os.makedirs(backup_dir, exist_ok=True)
        self._log(f"  Backup v10: {yaml_name}_v10/", 'dim')
        total = len(self.kicad10_files)
        ok = 0
        for fp in list(self.kicad10_files):
            bn = os.path.basename(fp)
            self._log(f"  {bn}...", 'dim')
            try:
                bak = os.path.join(backup_dir, bn)
                shutil.copy2(fp, bak)
                if convert_file_10to9(bak, self.project_dir, lambda m: self._log(m, 'dim')):
                    ok += 1
                    self._log(f"    OK", 'ok')
            except Exception as e:
                self._log(f"    ERROR: {e}", 'err')
        if not any(f.endswith('.kicad_pro') for f in os.listdir(self.project_dir)):
            pp = generate_kicad_pro(pn, self.project_dir)
            self._log(f"  Generado: {os.path.basename(pp)}", 'dim')
        self._log(f"Conversion: {ok}/{total} archivos\n", 'ok' if ok == total else 'warn')
        return ok

    def _convert_dialog(self):
        win = tk.Toplevel(self); win.title("Convertir KiCad 10 -> 9")
        win.geometry("620x460"); win.configure(bg=XP['bg'])
        win.transient(self); win.grab_set()

        # title
        t = tk.Frame(win, bg=XP['title_bg'], height=28)
        t.pack(fill='x'); t.pack_propagate(False)
        tk.Label(t, text="  Convertir KiCad 10 -> 9", fg='white', bg=XP['title_bg'],
                 font=("Tahoma", 10, "bold")).pack(side='left')

        body = tk.Frame(win, bg=XP['bg']); body.pack(fill='both', expand=True, padx=8, pady=6)

        pn = get_project_name(self.project_dir) or "proyecto"

        yaml_name = Path(self.yaml_path).stem
        backup_dir = os.path.join(self.project_dir, f"{yaml_name}_v10")

        info = tk.LabelFrame(body, text="  Informacion  ", bg=XP['panel_bg'], fg=XP['info'],
                              font=("Tahoma", 8, "bold"), relief='groove', bd=2)
        info.pack(fill='x', pady=(0,6))
        tk.Label(info, text=f"Proyecto: {pn}", bg=XP['panel_bg'], font=("Tahoma", 9, "bold"),
                 anchor='w').pack(fill='x', padx=6, pady=2)
        tk.Label(info, text=f"Originales v10 se moveran a:  {yaml_name}_v10/",
                 bg=XP['panel_bg'], fg=XP['warn'], font=("Tahoma", 8), anchor='w').pack(fill='x', padx=6)
        tk.Label(info, text=f"Convertidos v9 quedaran en la raiz junto al YAML",
                 bg=XP['panel_bg'], fg=XP['ok'], font=("Tahoma", 8), anchor='w').pack(fill='x', padx=6, pady=(0,4))

        # file list
        flf = tk.LabelFrame(body, text="  Archivos  ", bg=XP['panel_bg'], fg=XP['info'],
                              font=("Tahoma", 8, "bold"), relief='groove', bd=2)
        flf.pack(fill='x', pady=(0,4))
        lb = tk.Listbox(flf, font=("Tahoma", 9), height=4, relief='sunken', bd=2, bg=XP['white'])
        lb.pack(fill='x', padx=4, pady=4)
        for fp in self.kicad10_files: lb.insert('end', f"  {os.path.basename(fp)}")

        bf = tk.Frame(flf, bg=XP['panel_bg'])
        bf.pack(fill='x', padx=4, pady=(0,4))
        XPButton(bf, text="Anadir archivos...", command=lambda: self._add_extra(lb),
                 width=130, height=24).pack(side='left')

        # log
        clog = scrolledtext.ScrolledText(body, bg=XP['terminal_bg'], fg=XP['terminal_fg'],
                                          font=("Lucida Console", 8) if IS_WINDOWS else ("Consolas", 8),
                                          wrap='word', height=7, relief='sunken', bd=2)
        clog.pack(fill='both', expand=True, pady=(0,4))

        def do_convert():
            os.makedirs(backup_dir, exist_ok=True)
            def lf(m): clog.insert('end', m+'\n'); clog.see('end'); win.update_idletasks()
            lf(f"Backup v10: {backup_dir}")
            lf(f"Convertidos v9: {self.project_dir}\n")
            ok = 0
            for fp in list(self.kicad10_files):
                bn = os.path.basename(fp)
                lf(f"-- {bn} --")
                try:
                    bak = os.path.join(backup_dir, bn)
                    shutil.copy2(fp, bak)
                    lf(f"  Backup: {bn} -> {yaml_name}_v10/")
                    if convert_file_10to9(bak, self.project_dir, lf):
                        ok += 1
                except Exception as e:
                    lf(f"  ERROR: {e}")
            if not any(f.endswith('.kicad_pro') for f in os.listdir(self.project_dir)):
                pp = generate_kicad_pro(pn, self.project_dir)
                lf(f"\nGenerado: {os.path.basename(pp)}")
            lf(f"\nResultado: {ok}/{len(self.kicad10_files)} convertidos")
            self._log(f"\nConversion OK: {ok}/{len(self.kicad10_files)}", 'ok')
            self._log(f"  Backup v10: {backup_dir}", 'info')
            self._log(f"  Convertidos en: {self.project_dir}", 'info')
            self.kicad10_detected = False; self.kicad10_files = []
            self.convert_btn.pack_forget()
            self._set_step('version','ok'); self._set_step('ready','ok')
            for w in self.btn_frame.winfo_children():
                if isinstance(w, XPButton): w.set_state(True)
            self.status_var.set(f"Proyecto v9 listo | {len(self.variants)} variantes")
            self._update_project_card()

        XPButton(body, text="Convertir ahora", command=do_convert, width=160, height=30).pack(pady=(4,0))

    def _add_extra(self, lb):
        files = filedialog.askopenfilenames(filetypes=[("KiCad","*.kicad_sch *.kicad_pcb"),("Todos","*.*")])
        for fp in files:
            if fp not in self.kicad10_files:
                self.kicad10_files.append(fp); lb.insert('end', f"  {os.path.basename(fp)}")

    # ── RUN VARIANT ──

    def _run_variant(self, var):
        if self.kicad10_detected:
            messagebox.showwarning("KiCad 10", "Primero convierta los archivos."); return
        name = var.get('name','')
        self._log(f"\n{'='*50}", 'dim')
        self._log(f"Ejecutando: {name}", 'info')
        self._set_step('ready','running'); self.progress.set_value(0.1)
        self.btn_cancel.set_state(True)
        self.status_var.set(f"Ejecutando: {name}...")

        if IS_WINDOWS:
            wy = wsl_path(self.yaml_path); wd = wsl_path(self.project_dir)
            full = f'cd "{wd}" && kibot -c "{wy}" -g variant={name}'
            cmd = ['wsl', 'bash', '-lc', full]
        else:
            cmd = ['kibot', '-c', self.yaml_path, '-g', f'variant={name}']
        self._log(f"$ {' '.join(cmd)}", 'dim')

        def run():
            try:
                self.current_proc = subprocess.Popen(cmd, cwd=None if IS_WINDOWS else self.project_dir,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', **POPEN_FLAGS)
                for line in self.current_proc.stdout: self.after(0, self._log, line.rstrip())
                self.current_proc.wait(); rc = self.current_proc.returncode; self.current_proc = None
                if rc == 0:
                    self.after(0, self._set_step, 'ready', 'ok')
                    self.after(0, self.progress.set_value, 1.0)
                    self.after(0, self._log, "Finalizado OK", 'ok')
                    self.after(0, self.status_var.set, f"{name} completado")
                    self.after(0, self._mark_variant, name, 'ok')
                elif rc in (-9, 137):
                    self.after(0, self._log, "Cancelado.", 'warn')
                    self.after(0, self._set_step, 'ready', 'ok')
                    self.after(0, self.status_var.set, "Cancelado")
                else:
                    self.after(0, self._set_step, 'ready', 'error')
                    self.after(0, self._log, f"Error (exit {rc})", 'err')
                    self.after(0, self.status_var.set, f"{name} fallo")
                    self.after(0, self._mark_variant, name, 'err')
            except FileNotFoundError:
                self.after(0, self._log, "ERROR: comando no encontrado", 'err')
            except Exception as e:
                self.after(0, self._log, f"ERROR: {e}", 'err')
            finally:
                self.after(0, self.btn_cancel.set_state, False)
                self.after(0, self.progress.set_value, 0)
        threading.Thread(target=run, daemon=True).start()

    def _cancel_process(self):
        if self.current_proc:
            try: self.current_proc.kill(); self._log("Cancelando...", 'warn')
            except: pass

    # ── NEW FEATURES ──

    def _update_project_card(self):
        path = self.yaml_path
        data = self._yaml_data
        nombre = get_project_name(self.project_dir) or Path(path).stem
        fecha = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%d/%m/%Y %H:%M")
        outputs = data.get('outputs', [])
        out_types = []
        for o in outputs:
            if isinstance(o, dict):
                ot = o.get('type', o.get('name', '?'))
                if ot and ot not in out_types:
                    out_types.append(ot)
        out_str = ", ".join(out_types) if out_types else "No especificados"
        ruta = self.project_dir
        if len(ruta) > 55:
            ruta = "..." + ruta[-52:]
        self.card_vars['nombre'].set(nombre)
        self.card_vars['variantes'].set(str(len(self.variants)))
        self.card_vars['version'].set(self.detected_version or "Desconocida")
        self.card_vars['fecha'].set(fecha)
        self.card_vars['outputs'].set(out_str)
        self.card_vars['ruta'].set(ruta)
        self.project_card.pack(fill='x', pady=(0,4), before=self.status_outer)

    def _mark_variant(self, name, state):
        btn = self.variant_buttons.get(name)
        if btn:
            color = '#90EE90' if state == 'ok' else '#FF9999'
            btn.config(bg=color, activebackground=color)
            btn.bind('<Leave>', lambda _e, c=color: btn.config(bg=c))
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        result = "  OK  " if state == 'ok' else "  FAIL"
        entry = f"[{ts}]  {name:<20}  {result}"
        self.hist_list.insert('end', entry)
        idx = self.hist_list.size() - 1
        self.hist_list.itemconfig(idx, fg=XP['ok'] if state == 'ok' else XP['err'])
        self.hist_list.see(idx)

    def _open_output_folder(self):
        folder = self.project_dir
        if folder and os.path.isdir(folder):
            if IS_WINDOWS:
                os.startfile(folder)
            else:
                subprocess.Popen(['xdg-open', folder])
        else:
            messagebox.showinfo("Carpeta", "Ruta de salida no disponible")

    def _export_log(self):
        path = filedialog.asksaveasfilename(
            title="Exportar log",
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")]
        )
        if path:
            content = self.log.get('1.0', 'end')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.status_var.set(f"Log exportado: {os.path.basename(path)}")

if __name__ == '__main__':
    app = KiBotGUI()
    app.mainloop()
