# kibot-variant-manager
Desktop GUI for managing KiBot PCB variants with automatic KiCad 10→9 conversion

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
variants:
  - name: '1300092_24V'
    comment: '24V version'
    type: ibom
    variants_whitelist: ' , 24V'
    file_id: _1300092_24V

  - name: '1300092_5V'
    comment: '5V version'
    type: ibom
    variants_whitelist: ' , 5V'
    file_id: _1300092_5V
```

## License

Internal use — TORSA
