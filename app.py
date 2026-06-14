import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import shutil
import tempfile
import threading
import fitz
import io
from PIL import Image
import pdf_core

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class DocumentViewer(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.doc_path = None
        self.loading = False
        
        self.zoom_level = 1.0
        self.layout_mode = "1-up" # "1-up", "2-up"
        self.selected_pages = set()
        self.page_cards = {} # mapping page_num -> frame
        self.page_images = {} # mapping page_num -> PIL Image
        
        # --- Viewer Top Toolbar ---
        self.toolbar = ctk.CTkFrame(self, height=45, fg_color="#1e1e1e", corner_radius=0)
        self.toolbar.pack(fill="x", padx=0, pady=0)
        self.toolbar.pack_propagate(False)
        
        # Layout / Zoom Controls (Left)
        self.btn_zoom_out = ctk.CTkButton(self.toolbar, text="-", width=30, command=self.zoom_out)
        self.btn_zoom_out.pack(side="left", padx=(10, 2), pady=5)
        self.lbl_zoom = ctk.CTkLabel(self.toolbar, text="100%", width=40)
        self.lbl_zoom.pack(side="left", padx=2, pady=5)
        self.btn_zoom_in = ctk.CTkButton(self.toolbar, text="+", width=30, command=self.zoom_in)
        self.btn_zoom_in.pack(side="left", padx=(2, 15), pady=5)
        
        self.btn_fit_w = ctk.CTkButton(self.toolbar, text="Fit Width", width=70, fg_color="#3b3b3b", command=self.fit_width)
        self.btn_fit_w.pack(side="left", padx=2, pady=5)
        self.btn_fit_p = ctk.CTkButton(self.toolbar, text="Fit Page", width=70, fg_color="#3b3b3b", command=self.fit_page)
        self.btn_fit_p.pack(side="left", padx=(2, 15), pady=5)
        
        self.btn_1up = ctk.CTkButton(self.toolbar, text="1-Up", width=50, fg_color="#3b3b3b", command=lambda: self.set_layout("1-up"))
        self.btn_1up.pack(side="left", padx=2, pady=5)
        self.btn_2up = ctk.CTkButton(self.toolbar, text="2-Up", width=50, fg_color="#3b3b3b", command=lambda: self.set_layout("2-up"))
        self.btn_2up.pack(side="left", padx=(2, 15), pady=5)

        # Context Actions (Right)
        self.btn_print = ctk.CTkButton(self.toolbar, text="Print", width=60, fg_color="purple", command=self.print_doc)
        self.btn_print.pack(side="right", padx=(5, 10), pady=5)
        self.btn_export = ctk.CTkButton(self.toolbar, text="Export IMG", width=80, fg_color="#2c6b2c", command=self.export_images)
        self.btn_export.pack(side="right", padx=5, pady=5)
        self.btn_ocr = ctk.CTkButton(self.toolbar, text="OCR", width=50, command=self.ocr_selected)
        self.btn_ocr.pack(side="right", padx=5, pady=5)
        self.btn_extract = ctk.CTkButton(self.toolbar, text="Extract", width=60, command=self.extract_selected)
        self.btn_extract.pack(side="right", padx=5, pady=5)
        self.btn_del = ctk.CTkButton(self.toolbar, text="Delete", width=50, fg_color="darkred", command=self.delete_selected)
        self.btn_del.pack(side="right", padx=5, pady=5)
        self.btn_rot = ctk.CTkButton(self.toolbar, text="Rotate", width=50, command=self.rotate_selected)
        self.btn_rot.pack(side="right", padx=5, pady=5)
        
        # Scrollable Canvas for Pages
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Bind Ctrl+Scroll
        self.master.bind("<Control-MouseWheel>", self.on_mouse_wheel)

    def on_mouse_wheel(self, event):
        if not self.doc_path: return
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def zoom_in(self):
        self.zoom_level += 0.2
        self.apply_zoom()

    def zoom_out(self):
        self.zoom_level = max(0.2, self.zoom_level - 0.2)
        self.apply_zoom()
        
    def fit_width(self):
        # Calculate roughly based on scroll frame width
        target_width = self.scroll_frame.winfo_width() - 60
        if self.layout_mode == "2-up": target_width = (target_width / 2) - 30
        
        if self.page_images and 0 in self.page_images:
            w = self.page_images[0].width
            self.zoom_level = target_width / max(1, w)
            self.apply_zoom()

    def fit_page(self):
        target_height = self.scroll_frame.winfo_height() - 60
        if self.page_images and 0 in self.page_images:
            h = self.page_images[0].height
            self.zoom_level = target_height / max(1, h)
            self.apply_zoom()
            
    def apply_zoom(self):
        self.lbl_zoom.configure(text=f"{int(self.zoom_level*100)}%")
        for p_num, card in self.page_cards.items():
            if p_num in self.page_images:
                pil_img = self.page_images[p_num]
                new_w = int(pil_img.width * self.zoom_level)
                new_h = int(pil_img.height * self.zoom_level)
                
                # We update the CTkImage size
                lbl = card.winfo_children()[0] # The label is the first child
                ctk_img = ctk.CTkImage(light_image=pil_img, size=(new_w, new_h))
                lbl.configure(image=ctk_img)
                lbl.image = ctk_img

    def set_layout(self, mode):
        self.layout_mode = mode
        self.render_layout()
        
    def render_layout(self):
        # Unpack everything
        for card in self.page_cards.values():
            card.grid_forget()
            card.pack_forget()
            
        col = 0
        row = 0
        max_cols = 2 if self.layout_mode == "2-up" else 1
        
        for p_num in sorted(self.page_cards.keys()):
            card = self.page_cards[p_num]
            if max_cols == 1:
                card.pack(pady=15, padx=20)
            else:
                card.grid(row=row, column=col, padx=10, pady=10)
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

    def toggle_select(self, page_num):
        if page_num in self.selected_pages:
            self.selected_pages.remove(page_num)
            self.page_cards[page_num].configure(border_width=0)
        else:
            self.selected_pages.add(page_num)
            self.page_cards[page_num].configure(border_width=3, border_color="#1f538d")

    # --- Context Actions ---
    def rotate_selected(self):
        if not self.selected_pages: return
        rot = {p: 90 for p in self.selected_pages}
        self.master.apply_modification(pdf_core.rotate_pages, rot)

    def delete_selected(self):
        if not self.selected_pages: return
        import fitz
        try:
            doc = fitz.open(self.doc_path)
            total = len(doc)
            doc.close()
            keep = [p for p in range(total) if p not in self.selected_pages]
            if not keep:
                messagebox.showwarning("Warning", "Cannot delete all pages.")
                return
            self.master.apply_modification(pdf_core.remove_pages, keep)
        except Exception as e:
            print(e)
            
    def extract_selected(self):
        if not self.selected_pages: return
        dir_path = filedialog.askdirectory(title="Select Directory to Save Extracted Pages")
        if not dir_path: return
        
        import fitz
        doc = fitz.open(self.doc_path)
        new_doc = fitz.open()
        for p in sorted(list(self.selected_pages)):
            new_doc.insert_pdf(doc, from_page=p, to_page=p)
        out_path = os.path.join(dir_path, "extracted_pages.pdf")
        new_doc.save(out_path)
        new_doc.close()
        doc.close()
        messagebox.showinfo("Success", f"Extracted to {out_path}")

    def export_images(self):
        pages = list(self.selected_pages) if self.selected_pages else None
        fmt = "png"
        dir_path = filedialog.askdirectory(title="Select Directory for Images")
        if not dir_path: return
        success, msg = pdf_core.export_to_images(self.doc_path, dir_path, fmt, pages)
        if success:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Error", msg)

    def ocr_selected(self):
        if not self.selected_pages: return
        self.master.apply_modification(pdf_core.ocr_pdf, "eng+mal", list(self.selected_pages))
        
    def print_doc(self):
        if not self.doc_path: return
        pdf_core.print_pdf(self.doc_path)

    # --- Rendering ---
    def load_document(self, pdf_path):
        self.doc_path = pdf_path
        self.clear_viewer()
        if not self.doc_path or not os.path.exists(self.doc_path):
            lbl = ctk.CTkLabel(self.scroll_frame, text="No Document Opened\nClick 'Open PDF' to begin.", font=ctk.CTkFont(size=20), text_color="gray")
            lbl.pack(expand=True, fill="both", pady=100)
            return

        self.loading = True
        
        def render_task():
            try:
                doc = fitz.open(self.doc_path)
                for i in range(len(doc)):
                    if not self.loading or self.doc_path != pdf_path: 
                        break
                    # Render standard DPI, we scale using CTkImage
                    pix = doc[i].get_pixmap(dpi=150)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    self.page_images[i] = img
                    self.scroll_frame.after(0, self._add_page, i)
                doc.close()
                self.scroll_frame.after(100, self.render_layout)
            except Exception as e:
                print(f"Error loading document: {e}")
        
        threading.Thread(target=render_task, daemon=True).start()

    def _add_page(self, page_num):
        pil_img = self.page_images[page_num]
        w = int(pil_img.width * self.zoom_level)
        h = int(pil_img.height * self.zoom_level)
        ctk_img = ctk.CTkImage(light_image=pil_img, size=(max(1, w), max(1, h)))
        
        card = ctk.CTkFrame(self.scroll_frame, fg_color="#2b2b2b", corner_radius=10)
        self.page_cards[page_num] = card
        
        lbl_img = ctk.CTkLabel(card, image=ctk_img, text="", cursor="hand2")
        lbl_img.image = ctk_img
        lbl_img.pack(pady=(10, 5), padx=10)
        
        # Click to Select
        lbl_img.bind("<Button-1>", lambda event, p=page_num: self.toggle_select(p))
        card.bind("<Button-1>", lambda event, p=page_num: self.toggle_select(p))
        
        # Context Menu
        def show_menu(event):
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label=f"--- Page {page_num + 1} ---", state="disabled")
            menu.add_command(label="Toggle Select", command=lambda: self.toggle_select(page_num))
            menu.tk_popup(event.x_root, event.y_root)
            
        lbl_img.bind("<Button-3>", show_menu)
        
        lbl_text = ctk.CTkLabel(card, text=f"Page {page_num + 1}", text_color="gray")
        lbl_text.pack(pady=(0, 10))
        
        if self.layout_mode == "1-up":
            card.pack(pady=15, padx=20)

    def clear_viewer(self):
        self.loading = False
        self.selected_pages.clear()
        self.page_cards.clear()
        self.page_images.clear()
        for w in self.scroll_frame.winfo_children():
            w.destroy()


class ToolConfigPanel(ctk.CTkFrame):
    def __init__(self, master, app_ref):
        super().__init__(master)
        self.app = app_ref
        
        self.btn_back = ctk.CTkButton(self, text="< Back to Tools", fg_color="transparent", border_width=1, command=self.app.show_tool_list)
        self.btn_back.pack(fill="x", padx=10, pady=(10, 20))
        
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=10)

    def clear(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

    def build_watermark_ui(self):
        self.clear()
        ctk.CTkLabel(self.content_frame, text="Watermark Document", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        tabview = ctk.CTkTabview(self.content_frame, height=150)
        tabview.pack(fill="x", pady=10)
        tabview.add("Text")
        tabview.add("Image")
        
        # Text Tab
        ctk.CTkLabel(tabview.tab("Text"), text="Watermark Text:").pack(pady=5)
        entry_text = ctk.CTkEntry(tabview.tab("Text"))
        entry_text.pack(fill="x", pady=5)
        
        # Image Tab
        img_var = ctk.StringVar(value="No image selected")
        image_path = [None]
        
        def select_img():
            file = filedialog.askopenfilename(title="Select Watermark Image", filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
            if file:
                image_path[0] = file
                img_var.set(os.path.basename(file))
                
        ctk.CTkButton(tabview.tab("Image"), text="Select Image", command=select_img).pack(pady=5)
        ctk.CTkLabel(tabview.tab("Image"), textvariable=img_var).pack(pady=5)
        
        def apply_watermark():
            if tabview.get() == "Text":
                text = entry_text.get()
                if not text:
                    messagebox.showwarning("Warning", "Enter text.")
                    return
                # Applying to all pages (pages=None)
                self.app.apply_modification(pdf_core.watermark_pdf, text, None, 0.3, None)
            else:
                if not image_path[0]:
                    messagebox.showwarning("Warning", "Select image.")
                    return
                self.app.apply_modification(pdf_core.watermark_pdf, None, image_path[0], 0.3, None)
                
        ctk.CTkButton(self.content_frame, text="Apply Watermark", command=apply_watermark, fg_color="blue").pack(pady=20, fill="x")

    def build_security_ui(self):
        self.clear()
        ctk.CTkLabel(self.content_frame, text="Security", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        mode_var = ctk.StringVar(value="encrypt")
        ctk.CTkRadioButton(self.content_frame, text="Encrypt (Lock)", variable=mode_var, value="encrypt").pack(pady=5, anchor="w")
        ctk.CTkRadioButton(self.content_frame, text="Decrypt (Unlock)", variable=mode_var, value="decrypt").pack(pady=5, anchor="w")
        
        ctk.CTkLabel(self.content_frame, text="Password:").pack(pady=(15, 0), anchor="w")
        entry_pass = ctk.CTkEntry(self.content_frame, show="*")
        entry_pass.pack(fill="x", pady=5)
        
        def apply_security():
            pwd = entry_pass.get()
            if not pwd:
                messagebox.showwarning("Warning", "Enter password.")
                return
            if mode_var.get() == "encrypt":
                self.app.apply_modification(pdf_core.encrypt_pdf, pwd)
            else:
                self.app.apply_modification(pdf_core.decrypt_pdf, pwd)
                
        ctk.CTkButton(self.content_frame, text="Apply Security", command=apply_security, fg_color="darkred").pack(pady=20, fill="x")

    def build_compress_ui(self):
        self.clear()
        ctk.CTkLabel(self.content_frame, text="Compress PDF", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        ctk.CTkLabel(self.content_frame, text="Reduces file size by applying Flate compression and removing duplicate assets.", wraplength=180).pack(pady=10)
        
        def apply_compress():
            self.app.apply_modification(pdf_core.compress_pdf)
            
        ctk.CTkButton(self.content_frame, text="Optimize Size", command=apply_compress, fg_color="green").pack(pady=20, fill="x")
        
    def build_split_ui(self):
        self.clear()
        ctk.CTkLabel(self.content_frame, text="Split / Extract", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        mode_var = ctk.StringVar(value="range")
        ctk.CTkRadioButton(self.content_frame, text="Extract Range (Single PDF)", variable=mode_var, value="range").pack(pady=5, anchor="w")
        ctk.CTkRadioButton(self.content_frame, text="Burst (Multiple PDFs)", variable=mode_var, value="burst").pack(pady=5, anchor="w")
        
        ctk.CTkLabel(self.content_frame, text="Start Page:").pack(pady=(15, 0), anchor="w")
        entry_start = ctk.CTkEntry(self.content_frame)
        entry_start.pack(fill="x", pady=5)
        
        ctk.CTkLabel(self.content_frame, text="End Page:").pack(pady=(5, 0), anchor="w")
        entry_end = ctk.CTkEntry(self.content_frame)
        entry_end.pack(fill="x", pady=5)
        
        def apply_split():
            mode = mode_var.get()
            start, end = 0, 0
            if mode == "range":
                try:
                    start = int(entry_start.get()) - 1
                    end = int(entry_end.get()) - 1
                except ValueError:
                    messagebox.showwarning("Warning", "Enter valid numbers.")
                    return
            
            if mode == "burst":
                dir_path = filedialog.askdirectory(title="Select Save Directory for Burst Files")
                if not dir_path: return
                success, msg = pdf_core.split_pdf(self.app.working_path, dir_path, mode, start, end)
                if success:
                    messagebox.showinfo("Success", "Files successfully burst into directory!")
                else:
                    messagebox.showerror("Error", msg)
            else:
                self.app.apply_modification(pdf_core.split_pdf, mode, start, end)
                
        ctk.CTkButton(self.content_frame, text="Split PDF", command=apply_split, fg_color="blue").pack(pady=20, fill="x")

    def build_metadata_ui(self):
        self.clear()
        ctk.CTkLabel(self.content_frame, text="Edit Metadata", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        entries = {}
        fields = ["title", "author", "subject", "keywords", "creator", "producer"]
        
        success, meta = False, {}
        if self.app.working_path:
            success, meta = pdf_core.get_metadata(self.app.working_path)
            
        for field in fields:
            ctk.CTkLabel(self.content_frame, text=field.capitalize() + ":").pack(anchor="w", pady=(5,0))
            entry = ctk.CTkEntry(self.content_frame)
            entry.pack(fill="x")
            if success and meta and meta.get(field):
                entry.insert(0, meta[field])
            entries[field] = entry
            
        def apply_meta():
            new_meta = {field: entry.get() for field, entry in entries.items()}
            self.app.apply_modification(pdf_core.edit_metadata, new_meta)
            
        ctk.CTkButton(self.content_frame, text="Update Metadata", command=apply_meta, fg_color="blue").pack(pady=20, fill="x")

    def build_ocr_ui(self):
        self.clear()
        ctk.CTkLabel(self.content_frame, text="Optical Character Recognition", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        ctk.CTkLabel(self.content_frame, text="OCR processing across the entire document.", wraplength=180).pack(pady=10)
        
        lang_var = ctk.StringVar(value="eng+mal")
        ctk.CTkRadioButton(self.content_frame, text="English + Malayalam", variable=lang_var, value="eng+mal").pack(pady=5, anchor="w")
        ctk.CTkRadioButton(self.content_frame, text="English Only", variable=lang_var, value="eng").pack(pady=5, anchor="w")
        ctk.CTkRadioButton(self.content_frame, text="Malayalam Only", variable=lang_var, value="mal").pack(pady=5, anchor="w")
        
        def apply_ocr():
            self.app.apply_modification(pdf_core.ocr_pdf, lang_var.get(), None)
            
        def apply_opt_ocr():
            self.app.apply_modification(pdf_core.optimize_and_ocr_pdf, lang_var.get(), None)
            
        ctk.CTkButton(self.content_frame, text="Standard OCR", command=apply_ocr, fg_color="green").pack(pady=15, fill="x")
        ctk.CTkButton(self.content_frame, text="Optimize & OCR", command=apply_opt_ocr, fg_color="purple").pack(pady=5, fill="x")

    def build_merge_ui(self):
        self.clear()
        ctk.CTkLabel(self.content_frame, text="Merge Documents", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        ctk.CTkLabel(self.content_frame, text="The currently open document will be placed FIRST. Select files to append to the end.", wraplength=180).pack(pady=10)
        
        files_to_append = []
        lbl_files = ctk.CTkLabel(self.content_frame, text="0 files selected", text_color="gray")
        
        def sel_files():
            files = filedialog.askopenfilenames(title="Select PDFs to Append", filetypes=[("PDF", "*.pdf")])
            for f in files:
                if f not in files_to_append:
                    files_to_append.append(f)
            lbl_files.configure(text=f"{len(files_to_append)} files selected")
            
        ctk.CTkButton(self.content_frame, text="Select Files to Append", command=sel_files).pack(pady=5, fill="x")
        lbl_files.pack(pady=5)
        
        def apply_merge():
            if not files_to_append:
                messagebox.showwarning("Warning", "Select files to append.")
                return
            all_files = [self.app.working_path] + files_to_append
            self.app.apply_modification(pdf_core.merge_pdfs, all_files)
            
        ctk.CTkButton(self.content_frame, text="Merge to Current", command=apply_merge, fg_color="green").pack(pady=20, fill="x")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Magnolia PDF Studio - Acrobat Style")
        self.geometry("1100x800")
        
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        icon_path = os.path.join(base_dir, "icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
            
        self.temp_dir = tempfile.mkdtemp(prefix="magnoliapdf_")
        self.source_path = None
        self.working_path = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Top Toolbar
        self.topbar = ctk.CTkFrame(self, height=60, corner_radius=0)
        self.topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.topbar.grid_propagate(False)
        
        self.btn_open = ctk.CTkButton(self.topbar, text="Open PDF", font=ctk.CTkFont(weight="bold"), command=self.open_pdf)
        self.btn_open.pack(side="left", padx=20, pady=15)
        
        self.btn_save = ctk.CTkButton(self.topbar, text="Save As...", command=self.save_as, state="disabled", fg_color="green")
        self.btn_save.pack(side="left", padx=10, pady=15)
        
        self.btn_revert = ctk.CTkButton(self.topbar, text="Revert to Original", command=self.revert_pdf, state="disabled", fg_color="darkred")
        self.btn_revert.pack(side="left", padx=10, pady=15)
        
        self.lbl_status = ctk.CTkLabel(self.topbar, text="Ready", text_color="gray")
        self.lbl_status.pack(side="right", padx=20, pady=15)

        # Main Viewer Space
        self.viewer = DocumentViewer(self, width=700)
        self.viewer.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Right Sidebar (Tools)
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=1, column=1, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        self.tool_list_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.tool_list_frame.pack(fill="both", expand=True)
        
        ctk.CTkLabel(self.tool_list_frame, text="All Tools", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 20))
        
        self.tool_panel = ToolConfigPanel(self.sidebar, self)
        
        self.add_tool_btn("Watermark", self.tool_panel.build_watermark_ui)
        self.add_tool_btn("Security", self.tool_panel.build_security_ui)
        self.add_tool_btn("Compress", self.tool_panel.build_compress_ui)
        self.add_tool_btn("Split / Extract", self.tool_panel.build_split_ui)
        self.add_tool_btn("Metadata", self.tool_panel.build_metadata_ui)
        self.add_tool_btn("Merge PDFs", self.tool_panel.build_merge_ui)
        self.add_tool_btn("OCR Text Recog", self.tool_panel.build_ocr_ui)
        
        self.viewer.load_document(None)
        
    def add_tool_btn(self, name, command_func):
        def wrapper():
            if not self.working_path:
                messagebox.showwarning("Warning", "Please open a PDF first.")
                return
            self.tool_list_frame.pack_forget()
            command_func()
            self.tool_panel.pack(fill="both", expand=True)
            
        ctk.CTkButton(self.tool_list_frame, text=name, command=wrapper, height=40).pack(fill="x", padx=20, pady=5)
        
    def show_tool_list(self):
        self.tool_panel.pack_forget()
        self.tool_list_frame.pack(fill="both", expand=True)

    def open_pdf(self):
        file = filedialog.askopenfilename(title="Open PDF", filetypes=[("PDF Files", "*.pdf")])
        if file:
            self.source_path = file
            self.working_path = os.path.join(self.temp_dir, "working.pdf")
            shutil.copy(self.source_path, self.working_path)
            self.viewer.load_document(self.working_path)
            self.btn_save.configure(state="normal")
            self.btn_revert.configure(state="normal")
            self.lbl_status.configure(text=f"Opened: {os.path.basename(file)}")
            self.show_tool_list()

    def revert_pdf(self):
        if self.source_path and messagebox.askyesno("Confirm Revert", "Revert all modifications?"):
            shutil.copy(self.source_path, self.working_path)
            self.viewer.load_document(self.working_path)
            self.lbl_status.configure(text="Reverted to original.")

    def save_as(self):
        if not self.working_path: return
        file = filedialog.asksaveasfilename(title="Save PDF As", defaultextension=".pdf", initialfile="modified.pdf")
        if file:
            shutil.copy(self.working_path, file)
            messagebox.showinfo("Success", "PDF Saved successfully!")

    def apply_modification(self, pdf_core_func, *args):
        if not self.working_path: return
        
        self.lbl_status.configure(text="Processing...")
        self.update_idletasks()
        
        temp_out = os.path.join(self.temp_dir, "temp_out.pdf")
        
        def run():
            success, msg = pdf_core_func(self.working_path, temp_out, *args)
            self.after(0, self._modification_done, success, msg, temp_out)
            
        threading.Thread(target=run, daemon=True).start()
        
    def _modification_done(self, success, msg, temp_out):
        if success:
            if os.path.exists(temp_out):
                shutil.copy(temp_out, self.working_path)
                os.remove(temp_out)
            self.viewer.load_document(self.working_path)
            self.lbl_status.configure(text="Modification applied successfully!")
            self.show_tool_list()
        else:
            self.lbl_status.configure(text="Error applying modification.")
            messagebox.showerror("Error", f"Failed: {msg}")

    def on_closing(self):
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except: pass
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
