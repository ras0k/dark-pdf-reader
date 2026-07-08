import tkinter as tk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF
from PIL import Image, ImageTk, ImageOps
from tkinterdnd2 import TkinterDnD, DND_FILES

class ContinuousDarkPDFReader:
    def __init__(self, root):
        self.root = root
        self.root.title("Continuous Dark PDF Viewer (Flicker-Free)")
        self.root.geometry("900x1000")
        self.root.configure(bg="#121212")

        self.doc = None
        self.zoom = 1.5  

        # --- VIRTUALIZATION STATES ---
        self.page_layouts = []  
        # Now tracks: {page_num: (item_id, tk_img, rendered_zoom)}
        self.active_pages = {}  

        # --- Top Control Bar ---
        self.controls = tk.Frame(root, bg="#1e1e1e", padx=10, pady=8)
        self.controls.pack(fill=tk.X)

        self.btn_open = tk.Button(self.controls, text="Open PDF", command=self.open_pdf, 
                                  bg="#333333", fg="white", relief=tk.FLAT, padx=15)
        self.btn_open.pack(side=tk.LEFT, padx=5)

        self.lbl_info = tk.Label(self.controls, text="Drag & Drop a PDF. Ctrl + Scroll to Zoom.", 
                                 bg="#1e1e1e", fg="#aaaaaa", font=("Arial", 10))
        self.lbl_info.pack(side=tk.LEFT, padx=15)

        # --- Viewport Area ---
        self.canvas_frame = tk.Frame(root, bg="#121212")
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, bg="#121212", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self._on_scrollbar)
        self.canvas.configure(yscrollcommand=self._on_canvas_scroll)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Bindings ---
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Control-MouseWheel>", self._on_zoom)
        self.canvas.bind("<Configure>", self._on_resize)

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.handle_drop)

    def open_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            self.load_pdf(file_path)

    def handle_drop(self, event):
        file_path = event.data.strip()
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]
            
        if file_path.lower().endswith('.pdf'):
            self.load_pdf(file_path)

    def load_pdf(self, file_path):
        try:
            self.doc = fitz.open(file_path)
            self.render_document_layout(force_clear=True)
            self.canvas.yview_moveto(0) # Reset scroll to top
            self.update_view()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open PDF:\n{e}")

    def render_document_layout(self, force_clear=False):
        """Calculates bounding boxes. Does NOT delete canvas items unless loading a new PDF."""
        if not self.doc:
            return

        if force_clear:
            self.canvas.delete("all")
            self.active_pages.clear()
            self.zoom = 1.5

        self.page_layouts.clear()

        y_offset = 20
        padding = 20
        max_width = 0

        for page_num in range(len(self.doc)):
            page = self.doc.load_page(page_num)
            
            w = page.rect.width * self.zoom
            h = page.rect.height * self.zoom

            self.page_layouts.append({
                'y0': y_offset,
                'y1': y_offset + h,
                'width': w,
                'height': h
            })

            if w > max_width:
                max_width = w

            y_offset += h + padding

        self.canvas.update_idletasks()
        center_x = max(450, self.canvas.winfo_width() / 2)
        
        self.canvas.config(scrollregion=(0, 0, max(max_width, center_x * 2), y_offset))

    def update_view(self):
        """Intelligently updates, creates, or deletes pages to prevent flickering."""
        if not self.doc or not self.page_layouts:
            return

        canvas_height = self.canvas.winfo_height()
        if canvas_height <= 1:
            self.canvas.update_idletasks()
            canvas_height = self.canvas.winfo_height()

        y_top = self.canvas.canvasy(0)
        y_bottom = self.canvas.canvasy(canvas_height)
        center_x = self.canvas.winfo_width() / 2

        buffer = 800 
        view_start = y_top - buffer
        view_end = y_bottom + buffer

        visible_pages = set()
        for page_num, layout in enumerate(self.page_layouts):
            if layout['y1'] >= view_start and layout['y0'] <= view_end:
                visible_pages.add(page_num)

        # 1. CLEANUP: Delete pages that scrolled completely out of view
        for p in list(self.active_pages.keys()):
            if p not in visible_pages:
                item_id, _, _ = self.active_pages.pop(p)
                self.canvas.delete(item_id)

        # 2. RENDER OR SWAP: Update pages currently in view
        for p in visible_pages:
            layout = self.page_layouts[p]
            needs_render = True
            
            # Check if we already have this page on canvas
            if p in self.active_pages:
                item_id, tk_img, rendered_zoom = self.active_pages[p]
                
                # If the zoom matches, just move it to the new coordinate in case layout shifted
                if rendered_zoom == self.zoom:
                    needs_render = False
                    self.canvas.coords(item_id, center_x, layout['y0'])

            # If it's newly visible OR needs a higher/lower resolution because of zoom
            if needs_render:
                page = self.doc.load_page(p)
                matrix = fitz.Matrix(self.zoom, self.zoom)
                pix = page.get_pixmap(matrix=matrix)

                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                dark_img = ImageOps.invert(img)
                tk_img = ImageTk.PhotoImage(dark_img)

                if p in self.active_pages:
                    # THE MAGIC FIX: Swap the image data on the existing canvas item instantly
                    item_id, _, _ = self.active_pages[p]
                    self.canvas.itemconfig(item_id, image=tk_img)
                    self.canvas.coords(item_id, center_x, layout['y0'])
                    self.active_pages[p] = (item_id, tk_img, self.zoom)
                else:
                    # It wasn't on screen at all, create it fresh
                    item_id = self.canvas.create_image(center_x, layout['y0'], anchor=tk.N, image=tk_img)
                    self.active_pages[p] = (item_id, tk_img, self.zoom)

    # --- Scroll & Zoom Handlers ---

    def _on_scrollbar(self, *args):
        self.canvas.yview(*args)
        self.update_view()

    def _on_canvas_scroll(self, *args):
        self.scrollbar.set(*args)
        self.update_view()

    def _on_mousewheel(self, event):
        if event.delta:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            self.update_view()

    def _on_zoom(self, event):
        if not self.doc:
            return
        
        old_zoom = self.zoom
        if event.delta > 0:
            self.zoom = min(self.zoom * 1.2, 4.0)
        else:
            self.zoom = max(self.zoom / 1.2, 0.4)

        if self.zoom == old_zoom:
            return

        # 1. Save scroll percentage
        current_v_pos = self.canvas.yview()[0]
        
        # 2. Recalculate layout borders (DOES NOT DELETE IMAGES)
        self.render_document_layout(force_clear=False)
        
        # 3. Restore scroll positioning against new layout
        self.canvas.yview_moveto(current_v_pos)
        
        # 4. Swap resolutions in-place
        self.update_view()

    def _on_resize(self, event):
        center_x = event.width / 2
        for item_id, _, _ in self.active_pages.values():
            _, current_y = self.canvas.coords(item_id)
            self.canvas.coords(item_id, center_x, current_y)
        self.update_view()

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = ContinuousDarkPDFReader(root)
    root.mainloop()