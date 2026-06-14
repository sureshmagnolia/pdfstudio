import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import pdf_core
import threading

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class FullPreviewWindow(ctk.CTkToplevel):
    def __init__(self, master, pdf_path, start_page):
        super().__init__(master)
        self.title("Full Page Preview")
        self.geometry("800x900")
        self.pdf_path = pdf_path
        self.current_page = start_page
        
        import fitz
        self.doc = fitz.open(self.pdf_path)
        self.total_pages = len(self.doc)
        
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.lbl_image = ctk.CTkLabel(self.scroll_frame, text="Loading...")
        self.lbl_image.pack(expand=True, fill="both")
        
        self.controls = ctk.CTkFrame(self)
        self.controls.pack(fill="x", side="bottom", pady=10)
        
        self.btn_prev = ctk.CTkButton(self.controls, text="< Previous", command=self.prev_page)
        self.btn_prev.pack(side="left", padx=20)
        
        self.lbl_info = ctk.CTkLabel(self.controls, text="")
        self.lbl_info.pack(side="left", expand=True)
        
        self.btn_next = ctk.CTkButton(self.controls, text="Next >", command=self.next_page)
        self.btn_next.pack(side="right", padx=20)
        
        self.render_page()
        
    def render_page(self):
        import io
        from PIL import Image
        self.lbl_info.configure(text=f"Page {self.current_page + 1} of {self.total_pages}")
        pix = self.doc[self.current_page].get_pixmap(dpi=150)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        img.thumbnail((1200, 1000))
        ctk_img = ctk.CTkImage(light_image=img, size=(img.width, img.height))
        self.lbl_image.configure(image=ctk_img, text="")
        self.lbl_image.image = ctk_img
        
    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.render_page()
            
    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.render_page()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Magnolia PDF Studio")
        self.geometry("1000x700")
        
        # Set window icon
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        icon_path = os.path.join(base_dir, "icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
            
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(12, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="PDF Studio", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_compress = ctk.CTkButton(self.sidebar_frame, text="Compress PDF", command=lambda: self.select_frame("compress"))
        self.btn_compress.grid(row=1, column=0, padx=20, pady=5)
        self.btn_remove = ctk.CTkButton(self.sidebar_frame, text="Organize Pages", command=lambda: self.select_frame("remove"))
        self.btn_remove.grid(row=2, column=0, padx=20, pady=5)
        self.btn_merge = ctk.CTkButton(self.sidebar_frame, text="Merge PDFs", command=lambda: self.select_frame("merge"))
        self.btn_merge.grid(row=3, column=0, padx=20, pady=5)
        self.btn_split = ctk.CTkButton(self.sidebar_frame, text="Split PDF", command=lambda: self.select_frame("split"))
        self.btn_split.grid(row=4, column=0, padx=20, pady=5)
        self.btn_booklet = ctk.CTkButton(self.sidebar_frame, text="Booklet Maker", command=lambda: self.select_frame("booklet"))
        self.btn_booklet.grid(row=5, column=0, padx=20, pady=5)
        
        self.btn_watermark = ctk.CTkButton(self.sidebar_frame, text="Watermark", command=lambda: self.select_frame("watermark"))
        self.btn_watermark.grid(row=6, column=0, padx=20, pady=5)
        self.btn_security = ctk.CTkButton(self.sidebar_frame, text="Security", command=lambda: self.select_frame("security"))
        self.btn_security.grid(row=7, column=0, padx=20, pady=5)
        self.btn_metadata = ctk.CTkButton(self.sidebar_frame, text="Metadata", command=lambda: self.select_frame("metadata"))
        self.btn_metadata.grid(row=8, column=0, padx=20, pady=5)
        
        self.btn_ocr = ctk.CTkButton(self.sidebar_frame, text="OCR (Eng/Mal)", command=lambda: self.select_frame("ocr"))
        self.btn_ocr.grid(row=9, column=0, padx=20, pady=5)
        self.btn_opt_ocr = ctk.CTkButton(self.sidebar_frame, text="Optimize & OCR", command=lambda: self.select_frame("opt_ocr"), fg_color="purple")
        self.btn_opt_ocr.grid(row=10, column=0, padx=20, pady=5)

        # Main frames
        self.frames = {}
        
        self.frames["compress"] = CompressFrame(self)
        self.frames["remove"] = OrganizeFrame(self)
        self.frames["merge"] = MergeFrame(self)
        self.frames["split"] = SplitFrame(self)
        self.frames["booklet"] = BookletFrame(self)
        self.frames["watermark"] = WatermarkFrame(self)
        self.frames["security"] = SecurityFrame(self)
        self.frames["metadata"] = MetadataFrame(self)
        self.frames["ocr"] = OCRFrame(self)
        self.frames["opt_ocr"] = OptimizeOCRFrame(self)

        for frame in self.frames.values():
            frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        self.select_frame("compress")

    def select_frame(self, name):
        for frame in self.frames.values():
            frame.grid_remove()
        self.frames[name].grid()


class BaseFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.input_file = None
        self.output_file = None

        self.preview_scroll = ctk.CTkScrollableFrame(self, width=250, height=500)
        self.preview_scroll.grid(row=0, column=1, rowspan=10, sticky="nsew", padx=20, pady=20)

    def update_preview(self, filepath):
        for w in self.preview_scroll.winfo_children():
            w.destroy()
            
        def load_thumbnails():
            try:
                import fitz, io
                from PIL import Image
                doc = fitz.open(filepath)
                for i in range(len(doc)):
                    if not self.winfo_exists() or self.input_file != filepath: break
                    
                    pix = doc[i].get_pixmap(dpi=36)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    img.thumbnail((200, 300))
                    ctk_img = ctk.CTkImage(light_image=img, size=(img.width, img.height))
                    
                    self.after(0, self._add_thumbnail, i, ctk_img, filepath)
                doc.close()
            except Exception as e:
                print("Thumbnail error:", e)
                
        threading.Thread(target=load_thumbnails, daemon=True).start()

    def _add_thumbnail(self, page_num, ctk_img, filepath):
        lbl = ctk.CTkLabel(self.preview_scroll, image=ctk_img, text=f"Page {page_num+1}", compound="top", pady=10)
        lbl.image = ctk_img
        lbl.pack(pady=5)
        lbl.bind("<Double-Button-1>", lambda e, p=page_num: self.open_full_preview(filepath, p))

    def open_full_preview(self, filepath, page_num):
        FullPreviewWindow(self, filepath, page_num)

    def select_input_file(self, label_var, title="Select PDF"):
        filetypes = [("PDF Files", "*.pdf")] if "PDF" in title else [("All Files", "*.*")]
        file = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if file:
            self.input_file = file
            label_var.set(f"Selected: {os.path.basename(file)}")
            self.update_preview(file)

    def select_output_file(self, label_var, default_ext=".pdf", default_name="output"):
        file = filedialog.asksaveasfilename(title="Save As", defaultextension=default_ext, initialfile=default_name)
        if file:
            self.output_file = file
            label_var.set(f"Save to: {os.path.basename(file)}")

    def run_async(self, func, *args):
        def task():
            success, msg = func(*args)
            if success:
                messagebox.showinfo("Success", "Operation completed successfully!")
            else:
                messagebox.showerror("Error", f"Operation failed:\n{msg}")
        threading.Thread(target=task, daemon=True).start()

class CompressFrame(BaseFrame):
    def __init__(self, master):
        super().__init__(master)
        self.lbl_title = ctk.CTkLabel(self, text="Compress PDF", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_title.grid(row=0, column=0, pady=(20, 40))

        self.input_var = ctk.StringVar(value="No file selected")
        self.btn_in = ctk.CTkButton(self, text="Select Input PDF", command=lambda: self.select_input_file(self.input_var))
        self.btn_in.grid(row=1, column=0, pady=10)
        self.lbl_in = ctk.CTkLabel(self, textvariable=self.input_var)
        self.lbl_in.grid(row=2, column=0, pady=(0, 20))

        self.out_var = ctk.StringVar(value="No output selected")
        self.btn_out = ctk.CTkButton(self, text="Select Save Location", command=lambda: self.select_output_file(self.out_var, default_name="compressed.pdf"))
        self.btn_out.grid(row=3, column=0, pady=10)
        self.lbl_out = ctk.CTkLabel(self, textvariable=self.out_var)
        self.lbl_out.grid(row=4, column=0, pady=(0, 40))

        self.btn_run = ctk.CTkButton(self, text="Run Compression", command=self.process, fg_color="green")
        self.btn_run.grid(row=5, column=0, pady=10)

    def process(self):
        if not self.input_file or not self.output_file:
            messagebox.showwarning("Warning", "Select input and output files.")
            return
        self.run_async(pdf_core.compress_pdf, self.input_file, self.output_file)

class OrganizeFrame(BaseFrame):
    def __init__(self, master):
        super().__init__(master)
        self.checkboxes = {}
        self.rotations = {}
        
        self.lbl_title = ctk.CTkLabel(self, text="Organize Pages", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_title.grid(row=0, column=0, pady=(20, 20))

        self.input_var = ctk.StringVar(value="No file selected")
        self.btn_in = ctk.CTkButton(self, text="Select Input PDF", command=lambda: self.select_input_file(self.input_var))
        self.btn_in.grid(row=1, column=0, pady=10)
        self.lbl_in = ctk.CTkLabel(self, textvariable=self.input_var)
        self.lbl_in.grid(row=2, column=0, pady=(0, 10))

        self.lbl_desc = ctk.CTkLabel(self, text="Tick to remove, or select rotation for pages in the preview pane.")
        self.lbl_desc.grid(row=3, column=0)

        self.out_var = ctk.StringVar(value="No output selected")
        self.btn_out = ctk.CTkButton(self, text="Select Save Location", command=lambda: self.select_output_file(self.out_var, default_name="organized.pdf"))
        self.btn_out.grid(row=5, column=0, pady=10)
        self.lbl_out = ctk.CTkLabel(self, textvariable=self.out_var)
        self.lbl_out.grid(row=6, column=0, pady=(0, 20))

        self.btn_run = ctk.CTkButton(self, text="Run Organizer", command=self.process, fg_color="blue", hover_color="darkblue")
        self.btn_run.grid(row=7, column=0, pady=10)

    def _add_thumbnail(self, page_num, ctk_img, filepath):
        container = ctk.CTkFrame(self.preview_scroll, fg_color="transparent")
        container.pack(pady=5, fill="x")
        
        lbl = ctk.CTkLabel(container, image=ctk_img, text="")
        lbl.image = ctk_img
        lbl.pack(pady=2)
        lbl.bind("<Double-Button-1>", lambda e, p=page_num: self.open_full_preview(filepath, p))
        
        var_rm = ctk.BooleanVar(value=False)
        self.checkboxes[page_num] = var_rm
        chk = ctk.CTkCheckBox(container, text=f"Remove Page {page_num+1}", variable=var_rm)
        chk.pack(pady=2)
        
        rot_var = ctk.StringVar(value="0°")
        self.rotations[page_num] = rot_var
        opt = ctk.CTkOptionMenu(container, values=["0°", "90°", "180°", "270°"], variable=rot_var)
        opt.pack(pady=2)

    def process(self):
        if not self.input_file or not self.output_file:
            messagebox.showwarning("Warning", "Select input and output files.")
            return
            
        remove_pages = [p for p, var in self.checkboxes.items() if var.get()]
        rotation_dict = {}
        for p, var in self.rotations.items():
            if not self.checkboxes[p].get() and var.get() != "0°":
                rotation_dict[p] = int(var.get().replace("°", ""))
                
        if not remove_pages and not rotation_dict:
            messagebox.showwarning("Warning", "No pages ticked for removal or rotation.")
            return
            
        import fitz
        doc = fitz.open(self.input_file)
        total = len(doc)
        doc.close()
        
        keep_pages = [p for p in range(total) if p not in remove_pages]
        
        def run_organize():
            temp_path = self.output_file + ".tmp.pdf" if rotation_dict else self.output_file
            if remove_pages:
                success, msg = pdf_core.remove_pages(self.input_file, temp_path, keep_pages)
                if not success: return False, msg
            else:
                import shutil
                shutil.copy(self.input_file, temp_path)
                
            if rotation_dict:
                # Re-map rotation indices since pages were removed
                new_rotation_dict = {}
                for old_idx, angle in rotation_dict.items():
                    if old_idx in keep_pages:
                        new_idx = keep_pages.index(old_idx)
                        new_rotation_dict[new_idx] = angle
                success, msg = pdf_core.rotate_pages(temp_path, self.output_file, new_rotation_dict)
                if os.path.exists(temp_path) and temp_path != self.output_file:
                    os.remove(temp_path)
                return success, msg
            return True, "Success"
            
        self.run_async(run_organize)

class MergeFrame(BaseFrame):
    def __init__(self, master):
        super().__init__(master)
        self.input_files = []
        self.lbl_title = ctk.CTkLabel(self, text="Merge PDFs", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_title.grid(row=0, column=0, pady=(20, 20))

        self.btn_in = ctk.CTkButton(self, text="Add PDFs", command=self.add_files)
        self.btn_in.grid(row=1, column=0, pady=10)

        self.list_frame = ctk.CTkScrollableFrame(self, height=150, width=400)
        self.list_frame.grid(row=2, column=0, pady=10)

        self.out_var = ctk.StringVar(value="No output selected")
        self.btn_out = ctk.CTkButton(self, text="Select Save Location", command=lambda: self.select_output_file(self.out_var, default_name="merged.pdf"))
        self.btn_out.grid(row=3, column=0, pady=10)
        self.lbl_out = ctk.CTkLabel(self, textvariable=self.out_var)
        self.lbl_out.grid(row=4, column=0, pady=(0, 20))

        self.btn_run = ctk.CTkButton(self, text="Run Merge", command=self.process, fg_color="green")
        self.btn_run.grid(row=5, column=0, pady=10)

    def render_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        for i, f in enumerate(self.input_files):
            row_frame = ctk.CTkFrame(self.list_frame)
            row_frame.pack(fill="x", pady=2)
            
            lbl = ctk.CTkLabel(row_frame, text=os.path.basename(f), anchor="w")
            lbl.pack(side="left", padx=10, fill="x", expand=True)
            
            btn_up = ctk.CTkButton(row_frame, text="↑", width=30, command=lambda idx=i: self.move_up(idx))
            btn_up.pack(side="left", padx=2)
            
            btn_down = ctk.CTkButton(row_frame, text="↓", width=30, command=lambda idx=i: self.move_down(idx))
            btn_down.pack(side="left", padx=2)
            
            btn_del = ctk.CTkButton(row_frame, text="X", width=30, fg_color="red", hover_color="darkred", command=lambda idx=i: self.remove_item(idx))
            btn_del.pack(side="left", padx=2)
            
        if self.input_files:
            # We clear the checkboxes dict just in case, though MergeFrame doesn't use it
            self.update_preview(self.input_files[0])
        else:
            for w in self.preview_scroll.winfo_children():
                w.destroy()

    def move_up(self, idx):
        if idx > 0:
            self.input_files[idx-1], self.input_files[idx] = self.input_files[idx], self.input_files[idx-1]
            self.render_list()

    def move_down(self, idx):
        if idx < len(self.input_files) - 1:
            self.input_files[idx+1], self.input_files[idx] = self.input_files[idx], self.input_files[idx+1]
            self.render_list()

    def remove_item(self, idx):
        self.input_files.pop(idx)
        self.render_list()

    def add_files(self):
        files = filedialog.askopenfilenames(title="Select PDFs", filetypes=[("PDF Files", "*.pdf")])
        for f in files:
            if f not in self.input_files:
                self.input_files.append(f)
        self.render_list()

    def process(self):
        if len(self.input_files) < 2 or not self.output_file:
            messagebox.showwarning("Warning", "Select at least 2 input files and an output file.")
            return
        self.run_async(pdf_core.merge_pdfs, self.input_files, self.output_file)

class BookletFrame(BaseFrame):
    def __init__(self, master):
        super().__init__(master)
        self.lbl_title = ctk.CTkLabel(self, text="Booklet Maker", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_title.grid(row=0, column=0, pady=(20, 40))

        self.input_var = ctk.StringVar(value="No file selected")
        self.btn_in = ctk.CTkButton(self, text="Select Input PDF", command=lambda: self.select_input_file(self.input_var))
        self.btn_in.grid(row=1, column=0, pady=10)
        self.lbl_in = ctk.CTkLabel(self, textvariable=self.input_var)
        self.lbl_in.grid(row=2, column=0, pady=(0, 20))

        self.paper_var = ctk.StringVar(value="A4")
        self.radio_a4 = ctk.CTkRadioButton(self, text="A4", variable=self.paper_var, value="A4")
        self.radio_a4.grid(row=3, column=0, pady=5)
        self.radio_a3 = ctk.CTkRadioButton(self, text="A3", variable=self.paper_var, value="A3")
        self.radio_a3.grid(row=4, column=0, pady=(5, 20))

        self.out_var = ctk.StringVar(value="No output selected")
        self.btn_out = ctk.CTkButton(self, text="Select Save Location", command=lambda: self.select_output_file(self.out_var, default_name="booklet.pdf"))
        self.btn_out.grid(row=5, column=0, pady=10)
        self.lbl_out = ctk.CTkLabel(self, textvariable=self.out_var)
        self.lbl_out.grid(row=6, column=0, pady=(0, 20))

        self.btn_run = ctk.CTkButton(self, text="Create Booklet", command=self.process, fg_color="green")
        self.btn_run.grid(row=7, column=0, pady=10)

    def process(self):
        if not self.input_file or not self.output_file:
            messagebox.showwarning("Warning", "Select input and output files.")
            return
        self.run_async(pdf_core.create_booklet, self.input_file, self.output_file, self.paper_var.get())

class OCRFrame(BaseFrame):
    def __init__(self, master):
        super().__init__(master)
        self.lbl_title = ctk.CTkLabel(self, text="OCR (English + Malayalam)", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_title.grid(row=0, column=0, pady=(20, 40))

        self.input_var = ctk.StringVar(value="No file selected")
        self.btn_in = ctk.CTkButton(self, text="Select Input PDF", command=lambda: self.select_input_file(self.input_var))
        self.btn_in.grid(row=1, column=0, pady=10)
        self.lbl_in = ctk.CTkLabel(self, textvariable=self.input_var)
        self.lbl_in.grid(row=2, column=0, pady=(0, 20))

        self.lang_var = ctk.StringVar(value="eng+mal")
        self.radio_both = ctk.CTkRadioButton(self, text="English + Malayalam", variable=self.lang_var, value="eng+mal")
        self.radio_both.grid(row=3, column=0, pady=5)
        self.radio_eng = ctk.CTkRadioButton(self, text="English Only", variable=self.lang_var, value="eng")
        self.radio_eng.grid(row=4, column=0, pady=5)
        self.radio_mal = ctk.CTkRadioButton(self, text="Malayalam Only", variable=self.lang_var, value="mal")
        self.radio_mal.grid(row=5, column=0, pady=(5, 20))

        self.out_var = ctk.StringVar(value="No output selected")
        self.btn_out = ctk.CTkButton(self, text="Select Save Location", command=lambda: self.select_output_file(self.out_var, default_name="ocr_result.pdf"))
        self.btn_out.grid(row=6, column=0, pady=10)
        self.lbl_out = ctk.CTkLabel(self, textvariable=self.out_var)
        self.lbl_out.grid(row=7, column=0, pady=(0, 20))

        self.btn_run = ctk.CTkButton(self, text="Run OCR", command=self.process, fg_color="green")
        self.btn_run.grid(row=8, column=0, pady=10)

    def process(self):
        if not self.input_file or not self.output_file:
            messagebox.showwarning("Warning", "Select input and output files.")
            return
        self.run_async(pdf_core.ocr_pdf, self.input_file, self.output_file, self.lang_var.get())

class OptimizeOCRFrame(BaseFrame):
    def __init__(self, master):
        super().__init__(master)
        self.lbl_title = ctk.CTkLabel(self, text="Optimize & OCR", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_title.grid(row=0, column=0, pady=(20, 40))

        self.input_var = ctk.StringVar(value="No file selected")
        self.btn_in = ctk.CTkButton(self, text="Select Input PDF", command=lambda: self.select_input_file(self.input_var))
        self.btn_in.grid(row=1, column=0, pady=10)
        self.lbl_in = ctk.CTkLabel(self, textvariable=self.input_var)
        self.lbl_in.grid(row=2, column=0, pady=(0, 20))

        self.lang_var = ctk.StringVar(value="eng+mal")
        self.radio_both = ctk.CTkRadioButton(self, text="English + Malayalam", variable=self.lang_var, value="eng+mal")
        self.radio_both.grid(row=3, column=0, pady=5)
        self.radio_eng = ctk.CTkRadioButton(self, text="English Only", variable=self.lang_var, value="eng")
        self.radio_eng.grid(row=4, column=0, pady=5)
        self.radio_mal = ctk.CTkRadioButton(self, text="Malayalam Only", variable=self.lang_var, value="mal")
        self.radio_mal.grid(row=5, column=0, pady=(5, 20))

        self.out_var = ctk.StringVar(value="No output selected")
        self.btn_out = ctk.CTkButton(self, text="Select Save Location", command=lambda: self.select_output_file(self.out_var, default_name="optimized_ocr.pdf"))
        self.btn_out.grid(row=6, column=0, pady=10)
        self.lbl_out = ctk.CTkLabel(self, textvariable=self.out_var)
        self.lbl_out.grid(row=7, column=0, pady=(0, 20))

        self.btn_run = ctk.CTkButton(self, text="Run Optimize & OCR", command=self.process, fg_color="purple")
        self.btn_run.grid(row=8, column=0, pady=10)

    def process(self):
        if not self.input_file or not self.output_file:
            messagebox.showwarning("Warning", "Select input and output files.")
            return
        self.run_async(pdf_core.optimize_and_ocr_pdf, self.input_file, self.output_file, self.lang_var.get())

class SplitFrame(BaseFrame):
    def __init__(self, master):
        super().__init__(master)
        self.lbl_title = ctk.CTkLabel(self, text="Split PDF", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_title.grid(row=0, column=0, pady=(20, 20))

        self.input_var = ctk.StringVar(value="No file selected")
        self.btn_in = ctk.CTkButton(self, text="Select Input PDF", command=lambda: self.select_input_file(self.input_var))
        self.btn_in.grid(row=1, column=0, pady=10)
        self.lbl_in = ctk.CTkLabel(self, textvariable=self.input_var)
        self.lbl_in.grid(row=2, column=0, pady=(0, 10))

        self.mode_var = ctk.StringVar(value="burst")
        self.radio_burst = ctk.CTkRadioButton(self, text="Burst (Extract all to single pages)", variable=self.mode_var, value="burst")
        self.radio_burst.grid(row=3, column=0, pady=5)
        self.radio_range = ctk.CTkRadioButton(self, text="Extract Range", variable=self.mode_var, value="range")
        self.radio_range.grid(row=4, column=0, pady=5)
        
        self.range_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.range_frame.grid(row=5, column=0, pady=10)
        ctk.CTkLabel(self.range_frame, text="Start Page:").pack(side="left", padx=5)
        self.entry_start = ctk.CTkEntry(self.range_frame, width=50)
        self.entry_start.pack(side="left")
        ctk.CTkLabel(self.range_frame, text="End Page:").pack(side="left", padx=5)
        self.entry_end = ctk.CTkEntry(self.range_frame, width=50)
        self.entry_end.pack(side="left")

        self.out_var = ctk.StringVar(value="No output directory selected")
        self.btn_out = ctk.CTkButton(self, text="Select Save Directory", command=self.select_out_dir)
        self.btn_out.grid(row=6, column=0, pady=10)
        self.lbl_out = ctk.CTkLabel(self, textvariable=self.out_var)
        self.lbl_out.grid(row=7, column=0, pady=(0, 20))

        self.btn_run = ctk.CTkButton(self, text="Run Split", command=self.process, fg_color="blue")
        self.btn_run.grid(row=8, column=0, pady=10)

    def select_out_dir(self):
        dir_path = filedialog.askdirectory(title="Select Save Directory")
        if dir_path:
            self.output_file = dir_path
            self.out_var.set(f"Directory: {os.path.basename(dir_path)}")

    def process(self):
        if not self.input_file or not self.output_file:
            messagebox.showwarning("Warning", "Select input file and output directory.")
            return
        
        mode = self.mode_var.get()
        start = 0
        end = 0
        if mode == "range":
            try:
                start = int(self.entry_start.get()) - 1
                end = int(self.entry_end.get()) - 1
            except ValueError:
                messagebox.showerror("Error", "Please enter valid page numbers.")
                return
                
        self.run_async(pdf_core.split_pdf, self.input_file, self.output_file, mode, start, end)


class WatermarkFrame(BaseFrame):
    def __init__(self, master):
        super().__init__(master)
        self.lbl_title = ctk.CTkLabel(self, text="Add Watermark", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_title.grid(row=0, column=0, pady=(20, 20))

        self.input_var = ctk.StringVar(value="No file selected")
        self.btn_in = ctk.CTkButton(self, text="Select Input PDF", command=lambda: self.select_input_file(self.input_var))
        self.btn_in.grid(row=1, column=0, pady=10)
        self.lbl_in = ctk.CTkLabel(self, textvariable=self.input_var)
        self.lbl_in.grid(row=2, column=0, pady=(0, 10))
        
        self.tabview = ctk.CTkTabview(self, width=300, height=150)
        self.tabview.grid(row=3, column=0, pady=10)
        self.tabview.add("Text")
        self.tabview.add("Image")
        
        # Text Tab
        ctk.CTkLabel(self.tabview.tab("Text"), text="Watermark Text:").pack(pady=5)
        self.entry_text = ctk.CTkEntry(self.tabview.tab("Text"), width=200)
        self.entry_text.pack(pady=5)
        
        # Image Tab
        self.img_var = ctk.StringVar(value="No image selected")
        ctk.CTkButton(self.tabview.tab("Image"), text="Select Image (PNG/JPG)", command=self.select_image).pack(pady=5)
        ctk.CTkLabel(self.tabview.tab("Image"), textvariable=self.img_var).pack(pady=5)
        self.image_path = None

        self.out_var = ctk.StringVar(value="No output selected")
        self.btn_out = ctk.CTkButton(self, text="Select Save Location", command=lambda: self.select_output_file(self.out_var, default_name="watermarked.pdf"))
        self.btn_out.grid(row=4, column=0, pady=10)
        self.lbl_out = ctk.CTkLabel(self, textvariable=self.out_var)
        self.lbl_out.grid(row=5, column=0, pady=(0, 20))

        self.btn_run = ctk.CTkButton(self, text="Apply Watermark", command=self.process, fg_color="blue")
        self.btn_run.grid(row=6, column=0, pady=10)

    def select_image(self):
        file = filedialog.askopenfilename(title="Select Watermark Image", filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if file:
            self.image_path = file
            self.img_var.set(os.path.basename(file))

    def process(self):
        if not self.input_file or not self.output_file:
            messagebox.showwarning("Warning", "Select input and output files.")
            return
            
        current_tab = self.tabview.get()
        text = None
        img = None
        
        if current_tab == "Text":
            text = self.entry_text.get()
            if not text:
                messagebox.showwarning("Warning", "Please enter watermark text.")
                return
        else:
            img = self.image_path
            if not img:
                messagebox.showwarning("Warning", "Please select an image.")
                return
                
        self.run_async(pdf_core.watermark_pdf, self.input_file, self.output_file, text, img, 0.3)


class SecurityFrame(BaseFrame):
    def __init__(self, master):
        super().__init__(master)
        self.lbl_title = ctk.CTkLabel(self, text="Security & Encryption", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_title.grid(row=0, column=0, pady=(20, 20))

        self.input_var = ctk.StringVar(value="No file selected")
        self.btn_in = ctk.CTkButton(self, text="Select Input PDF", command=lambda: self.select_input_file(self.input_var))
        self.btn_in.grid(row=1, column=0, pady=10)
        self.lbl_in = ctk.CTkLabel(self, textvariable=self.input_var)
        self.lbl_in.grid(row=2, column=0, pady=(0, 10))

        self.mode_var = ctk.StringVar(value="encrypt")
        self.radio_enc = ctk.CTkRadioButton(self, text="Encrypt (Add Password)", variable=self.mode_var, value="encrypt")
        self.radio_enc.grid(row=3, column=0, pady=5)
        self.radio_dec = ctk.CTkRadioButton(self, text="Decrypt (Remove Password)", variable=self.mode_var, value="decrypt")
        self.radio_dec.grid(row=4, column=0, pady=5)
        
        ctk.CTkLabel(self, text="Password:").grid(row=5, column=0, pady=(10, 0))
        self.entry_pass = ctk.CTkEntry(self, width=200, show="*")
        self.entry_pass.grid(row=6, column=0, pady=5)

        self.out_var = ctk.StringVar(value="No output selected")
        self.btn_out = ctk.CTkButton(self, text="Select Save Location", command=lambda: self.select_output_file(self.out_var, default_name="secured.pdf"))
        self.btn_out.grid(row=7, column=0, pady=10)
        self.lbl_out = ctk.CTkLabel(self, textvariable=self.out_var)
        self.lbl_out.grid(row=8, column=0, pady=(0, 20))

        self.btn_run = ctk.CTkButton(self, text="Execute", command=self.process, fg_color="darkred")
        self.btn_run.grid(row=9, column=0, pady=10)

    def process(self):
        if not self.input_file or not self.output_file:
            messagebox.showwarning("Warning", "Select input and output files.")
            return
            
        password = self.entry_pass.get()
        if not password:
            messagebox.showwarning("Warning", "Please enter a password.")
            return
            
        if self.mode_var.get() == "encrypt":
            self.run_async(pdf_core.encrypt_pdf, self.input_file, self.output_file, password)
        else:
            self.run_async(pdf_core.decrypt_pdf, self.input_file, self.output_file, password)


class MetadataFrame(BaseFrame):
    def __init__(self, master):
        super().__init__(master)
        self.lbl_title = ctk.CTkLabel(self, text="PDF Metadata", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_title.grid(row=0, column=0, pady=(20, 20))

        self.input_var = ctk.StringVar(value="No file selected")
        self.btn_in = ctk.CTkButton(self, text="Select Input PDF", command=self.load_metadata)
        self.btn_in.grid(row=1, column=0, pady=10)
        self.lbl_in = ctk.CTkLabel(self, textvariable=self.input_var)
        self.lbl_in.grid(row=2, column=0, pady=(0, 10))
        
        self.entries = {}
        fields = ["title", "author", "subject", "keywords", "creator", "producer"]
        for i, field in enumerate(fields):
            f = ctk.CTkFrame(self, fg_color="transparent")
            f.grid(row=3+i, column=0, pady=2)
            ctk.CTkLabel(f, text=f"{field.capitalize()}:", width=80, anchor="e").pack(side="left", padx=5)
            entry = ctk.CTkEntry(f, width=200)
            entry.pack(side="left")
            self.entries[field] = entry

        self.out_var = ctk.StringVar(value="No output selected")
        self.btn_out = ctk.CTkButton(self, text="Select Save Location", command=lambda: self.select_output_file(self.out_var, default_name="meta_updated.pdf"))
        self.btn_out.grid(row=10, column=0, pady=10)
        self.lbl_out = ctk.CTkLabel(self, textvariable=self.out_var)
        self.lbl_out.grid(row=11, column=0, pady=(0, 20))

        self.btn_run = ctk.CTkButton(self, text="Save Metadata", command=self.process, fg_color="blue")
        self.btn_run.grid(row=12, column=0, pady=10)
        
    def load_metadata(self):
        self.select_input_file(self.input_var)
        if self.input_file:
            success, meta = pdf_core.get_metadata(self.input_file)
            if success and meta:
                for field, entry in self.entries.items():
                    entry.delete(0, 'end')
                    if meta.get(field):
                        entry.insert(0, meta[field])

    def process(self):
        if not self.input_file or not self.output_file:
            messagebox.showwarning("Warning", "Select input and output files.")
            return
            
        new_meta = {field: entry.get() for field, entry in self.entries.items()}
        self.run_async(pdf_core.edit_metadata, self.input_file, self.output_file, new_meta)

if __name__ == "__main__":
    app = App()
    app.mainloop()
