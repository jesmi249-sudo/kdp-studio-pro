# KDP Studio Pro

A professional offline Windows desktop application for generating Amazon KDP content.

## Features
- Modular Clean Architecture
- CustomTkinter UI
- Offline generation of KDP interiors and covers.
- Metadata Generator (JSON/CSV)
- Production-ready Standalone Executable

## Setup
1. Create a virtual environment: `python -m venv .venv`
2. Activate: `.venv\Scripts\activate`
3. Install requirements: `pip install -r requirements.txt`

## Run
Use `run.bat` or run `python main.py` directly.

## Build for Production
Run `build.bat` to compile the application into a standalone `.exe`.
The build process uses PyInstaller and applies the application icon, version metadata, and optimizes loading speed by stripping unused binaries.

## License
MIT License. See [LICENSE](LICENSE) for details.
