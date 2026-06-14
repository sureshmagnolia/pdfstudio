import sys
import os
from cx_Freeze import setup, Executable
import customtkinter

# Get the path to customtkinter's assets so they are properly bundled
customtkinter_path = os.path.dirname(customtkinter.__file__)

build_exe_options = {
    "packages": ["os", "sys", "fitz", "pytesseract", "PIL", "tkinter", "customtkinter"],
    "include_files": [
        (customtkinter_path, "customtkinter"), # Required for modern UI rendering
        ("tessdata", "tessdata"),              # Language packs
        (r"C:\Program Files\Tesseract-OCR", "Tesseract-OCR"), # The OCR engine itself (~240MB)
        ("icon.ico", "icon.ico"),              # App icon
    ],
    "excludes": ["unittest", "email", "http", "xml", "pydoc"]
}

# Hide the console window
base = "gui" if sys.platform == "win32" else None

bdist_msi_options = {
    "add_to_path": False,
    "initial_target_dir": r"[ProgramFilesFolder]\Magnolia PDF Studio",
}

setup(
    name="Magnolia PDF Studio",
    version="1.0",
    description="Magnolia PDF Studio - PDF Editing, Compression, and OCR",
    options={
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options,
    },
    executables=[
        Executable(
            "app.py", 
            base=base, 
            target_name="Magnolia PDF Studio.exe",
            shortcut_name="Magnolia PDF Studio",
            shortcut_dir="DesktopFolder",
            icon="icon.ico"
        )
    ]
)
