# KiBot Variant Manager

## Contexto
GUI de escritorio en Python/tkinter para gestionar variantes de PCB con KiBot.
Incluye conversión automática KiCad 10→9 mediante parser S-expression.
Se ejecuta como .exe en Windows, llama a KiBot a través de WSL.

## Stack
- Python 3.13, tkinter, tkinterdnd2
- PyInstaller para generar .exe
- KiBot se ejecuta en WSL

## Reglas
- Estilo visual Windows XP con colores corporativos TORSA (rojo #C8102E)
- Los archivos originales KiCad 10 NUNCA se modifican, van a carpeta _v10
- Los convertidos v9 quedan en la raíz junto al YAML
- Fuente UI: Tahoma
- Sin emojis en la interfaz
- Código en inglés, interfaz en español