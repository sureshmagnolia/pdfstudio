import fitz  # PyMuPDF
import os
import sys
import pytesseract
from PIL import Image
import io

if getattr(sys, 'frozen', False):
    # Running in a bundled executable
    base_dir = os.path.dirname(sys.executable)
    tess_path = os.path.join(base_dir, "Tesseract-OCR", "tesseract.exe")
    tessdata_path = os.path.join(base_dir, "tessdata")
else:
    # Running in a normal Python environment
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tess_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    tessdata_path = os.path.join(base_dir, "tessdata")

pytesseract.pytesseract.tesseract_cmd = tess_path
TESSDATA_DIR = tessdata_path

def compress_pdf(input_path, output_path):
    """Compresses a PDF aggressively by downsampling images safely using PyMuPDF natively."""
    try:
        doc = fitz.open(input_path)
        processed_xrefs = set()
        
        for i in range(len(doc)):
            page = doc[i]
            images = page.get_images()
            for img in images:
                xref = img[0]
                smask = img[1]
                
                if xref in processed_xrefs:
                    continue
                processed_xrefs.add(xref)
                
                try:
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n - pix.alpha > 3:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                    has_smask = smask > 0
                    mask_pix = None
                    
                    if has_smask:
                        mask_pix = fitz.Pixmap(doc, smask)
                    elif pix.alpha:
                        mask_pix = fitz.Pixmap(pix.alpha_map())
                        pix = fitz.Pixmap(pix, 0)
                        
                    shrink_count = 0
                    while pix.width > 1200 or pix.height > 1200:
                        pix.shrink(1)
                        shrink_count += 1
                        
                    if mask_pix and shrink_count > 0:
                        for _ in range(shrink_count):
                            mask_pix.shrink(1)
                            
                    xref_obj_str = str(doc.xref_object(xref))
                    is_jpeg = "DCTDecode" in xref_obj_str or "JPXDecode" in xref_obj_str
                    has_alpha = mask_pix is not None
                    
                    if has_alpha or not is_jpeg:
                        doc.update_stream(xref, pix.samples, compress=True)
                        doc.xref_set_key(xref, "Filter", "/FlateDecode")
                        doc.xref_set_key(xref, "ColorSpace", "/DeviceRGB" if pix.n == 3 else "/DeviceGray")
                        doc.xref_set_key(xref, "BitsPerComponent", "8")
                        doc.xref_set_key(xref, "Width", str(pix.width))
                        doc.xref_set_key(xref, "Height", str(pix.height))
                        doc.xref_set_key(xref, "DecodeParms", "null")
                        doc.xref_set_key(xref, "ColorTransform", "null")
                        doc.xref_set_key(xref, "Mask", "null")
                        
                        if has_alpha:
                            if not has_smask:
                                smask = doc.get_new_xref()
                                doc.update_object(smask, "<<>>")
                            
                            doc.update_stream(smask, mask_pix.samples, compress=True)
                            doc.xref_set_key(smask, "Type", "/XObject")
                            doc.xref_set_key(smask, "Subtype", "/Image")
                            doc.xref_set_key(smask, "Filter", "/FlateDecode")
                            doc.xref_set_key(smask, "Width", str(mask_pix.width))
                            doc.xref_set_key(smask, "Height", str(mask_pix.height))
                            doc.xref_set_key(smask, "ColorSpace", "/DeviceGray")
                            doc.xref_set_key(smask, "BitsPerComponent", "8")
                            doc.xref_set_key(smask, "DecodeParms", "null")
                            doc.xref_set_key(xref, "SMask", f"{smask} 0 R")
                    else:
                        jpeg_bytes = pix.tobytes("jpeg", 60)
                        doc.update_stream(xref, jpeg_bytes, compress=False)
                        doc.xref_set_key(xref, "Filter", "/DCTDecode")
                        doc.xref_set_key(xref, "ColorSpace", "/DeviceRGB" if pix.n == 3 else "/DeviceGray")
                        doc.xref_set_key(xref, "BitsPerComponent", "8")
                        doc.xref_set_key(xref, "Width", str(pix.width))
                        doc.xref_set_key(xref, "Height", str(pix.height))
                        doc.xref_set_key(xref, "DecodeParms", "null")
                        doc.xref_set_key(xref, "ColorTransform", "null")
                        doc.xref_set_key(xref, "Mask", "null")
                        doc.xref_set_key(xref, "SMask", "null")
                        
                except Exception as img_e:
                    print(f"Skipping image {xref} due to error: {img_e}")
                    continue
                    
        doc.save(
            output_path,
            garbage=4,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            clean=True
        )
        doc.close()
        return True, "Success"
    except Exception as e:
        return False, str(e)

def remove_pages(input_path, output_path, pages_to_keep):
    """Removes pages. pages_to_keep is a list of 0-indexed page numbers."""
    try:
        doc = fitz.open(input_path)
        doc.select(pages_to_keep)
        doc.save(output_path)
        doc.close()
        return True, "Success"
    except Exception as e:
        return False, str(e)

def merge_pdfs(input_paths, output_path):
    """Merges multiple PDFs into one."""
    try:
        result_doc = fitz.open()
        for path in input_paths:
            with fitz.open(path) as doc:
                result_doc.insert_pdf(doc)
        result_doc.save(output_path)
        result_doc.close()
        return True, "Success"
    except Exception as e:
        return False, str(e)

def create_booklet(input_path, output_path, paper_size="A4"):
    """
    Creates a booklet layout. Rearranges pages for saddle-stitch binding.
    """
    try:
        doc = fitz.open(input_path)
        page_count = len(doc)
        
        # Calculate target multiple of 4
        target_pages = ((page_count + 3) // 4) * 4
        
        # Add blank pages if necessary
        for _ in range(target_pages - page_count):
            doc.new_page()
            
        booklet_doc = fitz.open()
        
        # Paper dimensions in points
        if paper_size.upper() == "A3":
            # A3 landscape: 1190 x 842 points
            w, h = 1190, 842
        else:
            # A4 landscape: 842 x 595 points
            w, h = 842, 595

        rect = fitz.Rect(0, 0, w, h)
        
        total_sheets = target_pages // 4
        
        for i in range(total_sheets):
            # Front side
            left_idx = target_pages - 1 - (2 * i)
            right_idx = 2 * i
            
            page_front = booklet_doc.new_page(width=w, height=h)
            page_front.show_pdf_page(fitz.Rect(0, 0, w/2, h), doc, left_idx)
            page_front.show_pdf_page(fitz.Rect(w/2, 0, w, h), doc, right_idx)
            
            # Back side
            left_idx = 2 * i + 1
            right_idx = target_pages - 2 - (2 * i)
            
            page_back = booklet_doc.new_page(width=w, height=h)
            page_back.show_pdf_page(fitz.Rect(0, 0, w/2, h), doc, left_idx)
            page_back.show_pdf_page(fitz.Rect(w/2, 0, w, h), doc, right_idx)
            
        booklet_doc.save(output_path)
        booklet_doc.close()
        doc.close()
        return True, "Success"
    except Exception as e:
        return False, str(e)

def ocr_pdf(input_path, output_path, lang="eng+mal"):
    """
    Performs OCR on the PDF and creates a new searchable PDF, 
    or simply extracts text and saves it to a text file.
    Since we want to preserve PDF format, we can use pytesseract's image_to_pdf_or_hocr
    """
    try:
        doc = fitz.open(input_path)
        merged_pdf = fitz.open()
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Render page to image (DPI=300 for good OCR)
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            
            # Get PDF bytes from pytesseract
            custom_config = f'--tessdata-dir "{TESSDATA_DIR}"'
            pdf_bytes = pytesseract.image_to_pdf_or_hocr(img, extension='pdf', lang=lang, config=custom_config)
            
            # Open the single page PDF and insert into merged
            with fitz.open("pdf", pdf_bytes) as pdf_page:
                merged_pdf.insert_pdf(pdf_page)
                
        merged_pdf.save(output_path)
        merged_pdf.close()
        doc.close()
        return True, "Success"
    except Exception as e:
        return False, str(e)

def optimize_and_ocr_pdf(input_path, output_path, lang="eng+mal"):
    """Runs OCR to create a clean text layer (removing junk), then aggressively compresses the images."""
    try:
        temp_ocr_path = output_path + ".temp.pdf"
        
        # Step 1: OCR (this rasterizes the page, removing old vector junk, and adds clean text)
        success, msg = ocr_pdf(input_path, temp_ocr_path, lang)
        if not success:
            return False, f"OCR Failed: {msg}"
            
        # Step 2: Compress the newly generated searchable PDF
        success, msg = compress_pdf(temp_ocr_path, output_path)
        
        # Cleanup temp file
        if os.path.exists(temp_ocr_path):
            os.remove(temp_ocr_path)
            
        if not success:
            return False, f"Compression Failed: {msg}"
            
        return True, "Success"
    except Exception as e:
        return False, str(e)
