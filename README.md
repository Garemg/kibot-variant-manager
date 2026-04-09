<p align="center">
  <img src="assets/icono.png" width="120" alt="KiBot Variant Manager">
</p>

# KiBot Variant Manager

Desktop tool for managing PCB variants using KiBot.
Generates production documentation (Gerbers, BOM, Pick & Place, PDFs)
for multiple variants of the same design from a visual interface.

## Features

- YAML configuration loading with drag & drop
- Variant button panel with direct KiBot execution
- Automatic KiCad version detection (7/8/9/10)
- Automatic KiCad 10 → 9 conversion for KiBot compatibility
- Original file backup in separate folder
- .kicad_pro generation for converted projects
- System requirements validation (WSL, KiCad, KiBot)
- Execution log in integrated terminal
- Windows XP style interface with corporate theme

## Requirements

- Windows 10/11 with WSL (Ubuntu)
- KiCad installed in WSL
- KiBot 1.8+ installed in WSL
- Python 3.10+ (development only)

## Installation

Download `KiBotManager.exe` from [Releases](../../releases) and run.
No additional installation required.

## Development

```bash
git clone https://github.com/TU_USUARIO/kibot-variant-manager.git
cd kibot-variant-manager
pip install -r requirements.txt
python kibot_gui.py
```

## Build .exe

```bash
pyinstaller --onefile --windowed --name KiBotManager --collect-all tkinterdnd2 kibot_gui.py
```

## YAML Structure

```yaml
kibot:
  version: 1

global:
    output: '%f_%V-%i.%x'
    out_dir: Generated/%f_%V
variants:
  - name: 'default'
    # comment: 'Minimal PCB no USB'
    type: ibom


outputs:
  - name: 'bom_xlsx'
    comment: "Spreadsheet for the Bill of Materials"
    type: bom
    dir: BoM
    options: &bom_options
      xlsx:
        datasheet_as_link: MFP
        title: '%f-%V'
        max_col_width: 40
        logo: 'Logo_Torsa.png'
        highlight_empty: false
      columns:
        - Row
        - References
        - Quantity Per PCB
        - field: Value
          join: ['Voltage DC', 'current', 'power', 'Tolerancia']
        - Torsa#
        - Footprint
        - Config
        - Footprint X
        - Footprint Y
        - Footprint Rot
        - Footprint Type
        - Footprint Side
        - Footprint Populate
        - Footprint X-Size
        - Footprint Y-Size
      normalize_values: true
      count_smd_tht: true

  - name: 'bom_html'
    comment: "HTML for the Bill of Materials"
    type: bom
    dir: BoM
    options:
      <<: *bom_options
      format: HTML
      html:
        title: '%f-%V'
        logo: 'Logo_Torsa.png'
        highlight_empty: false

  - name: 'ibom'
    comment: 'Prototype mounting guide'
    type: ibom
    dir: BoM
    options:
      layer_view: FB
     
  - name: gerbers
    comment: Gerbers
    type: gerber
    dir: Gerbers_Standard
    options:
      use_gerber_x2_attributes: true   
      exclude_edge_layer: false    
      tent_vias: true
    layers:
      - copper
      - Edge.Cuts
      - F.SilkS
      - B.SilkS
      - F.Mask
      - B.Mask
      - F.Paste
      - B.Paste
      - F.Adhes
      - B.Adhes

  - name: gerbers_protel
    comment: Gerbers
    type: gerber
    dir: Gerbers_Protel
    options:
      use_protel_extensions: true
      use_gerber_x2_attributes: true   
      exclude_edge_layer: false          
      tent_vias: true
    layers:
      - copper
      - Edge.Cuts
      - F.SilkS
      - B.SilkS
      - F.Mask
      - B.Mask
      - F.Paste
      - B.Paste
      - F.Adhes
      - B.Adhes

  - name: drill
    comment: Drill files
    type: excellon
    dir: Gerbers_Standard
    options:
      map:
        type: pdf
      pth_and_npth_single_file: true
      
  - name: drill_protel
    comment: Drill files
    type: excellon
    dir: Gerbers_Protel
    options:
      map:
        type: pdf
      pth_and_npth_single_file: true

  - name: position
    comment: Pick & Place
    type: position
    dir: Position
    options:
      separate_files_for_front_and_back: true

  - name: print_pdf
    comment: "PDF for the PCB"
    type: pcb_print
    dir: PCB
    options:
      force_edge_cuts: true
      keep_temporal_files: true
      title: "Assembly Map"
      scaling: 1.0
      pages:
        - layers: [F.Fab, F.Courtyard, Edge.Cuts]
          sheet: 'Fabrication Top layers'
        - layers: [B.Fab, B.Courtyard, Edge.Cuts]
          sheet: 'Fabrication Bottom layers'
          mirror: true
          
  - name: 3D
    comment: "STEP 3D model"
    type: step
    dir: 3D

  # - name: board_top
    # comment: "Top layer view"
    # type: pcbdraw
    # dir: PCB
    # options:
      # format: jpg
      # dpi: 300

  # - name: board_top_filled
  #   comment: "Top layer view with components"
  #   type: pcbdraw
  #   dir: PCB
  #   options:
  #     format: jpg
  #     dpi: 300
  #     output: '%f-%i%v-filled.%x'

  # - name: board_bottom
    # comment: "Bottom layer view"
    # type: pcbdraw
    # dir: PCB
    # options:
      # format: jpg
      # dpi: 300
      # bottom: true

  # - name: board_bottom_filled
    # comment: "Bottom layer view with components"
    # type: pcbdraw
    # dir: PCB
    # options:
      # format: jpg
      # dpi: 300
      # bottom: true
      # output: '%f-%i%v-filled.%x'

```

## License

Internal use — TORSA
