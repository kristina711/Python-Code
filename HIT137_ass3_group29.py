import tkinter as tk
from tkinter import filedialog, simpledialog
from PIL import Image, ImageTk
import requests
from io import BytesIO
import copy
import cv2
import numpy as np

class ImageCropper:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Crop & Resize")
        
        self.canvas = tk.Canvas(root, cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        
        self.btn_frame = tk.Frame(root)
        self.btn_frame.pack(fill="x")
        
        self.url_entry = tk.Entry(self.btn_frame, width=40)
        self.url_entry.pack(side="left", padx=5, pady=5)
        tk.Button(self.btn_frame, text="Load from URL", command=self.load_from_url).pack(side="left")
        tk.Button(self.btn_frame, text="Load from File", command=self.load_from_file).pack(side="left")
        tk.Button(self.btn_frame, text="Save Image", command=self.save_image).pack(side="left")
        tk.Button(self.btn_frame, text="Undo", command=self.undo).pack(side="left")
        tk.Button(self.btn_frame, text="Redo", command=self.redo).pack(side="left")
        tk.Button(self.btn_frame, text="Resize Image", command=self.resize_image).pack(side="left")
        tk.Button(self.btn_frame, text="Edge Detection", command=self.apply_edge_detection).pack(side="left")

        self.status_label = tk.Label(root, text="Load an image to start cropping.")
        self.status_label.pack()

        self.img = None
        self.tk_img = None
        self.start_x = self.start_y = None
        self.rect_id = None
        
        self.history = []  # Stack to keep track of image history for undo/redo
        self.future = []  # Stack for redo actions

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def load_from_url(self):
        url = self.url_entry.get()
        try:
            response = requests.get(url)
            response.raise_for_status()
            self.img = Image.open(BytesIO(response.content))
            self.add_to_history()  # Add to history after loading
            self.display_image()
        except Exception as e:
            self.status_label.config(text=f"Error: {e}")

    def load_from_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.png;*.jpeg")])
        if file_path:
            self.img = Image.open(file_path)
            self.add_to_history()  # Add to history after loading
            self.display_image()

    def display_image(self):
        if self.tk_img:
            self.canvas.delete(self.canvas.find_all())  # Clear previous image

        self.img = self.img.convert("RGB")  # Ensure it's in RGB mode
        self.tk_img = ImageTk.PhotoImage(self.img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self.canvas.config(width=self.img.width, height=self.img.height)
        self.status_label.config(text="Select a region to crop.")

    def on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=2)

    def on_drag(self, event):
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        if not self.img or self.start_x is None or self.start_y is None:
            return
        
        # Ensure coordinates are sorted correctly
        x1, x2 = sorted([self.start_x, event.x])
        y1, y2 = sorted([self.start_y, event.y])

        # Ensure coordinates are within image bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(self.img.width, x2), min(self.img.height, y2)

        # Crop and resize
        cropped = self.img.crop((x1, y1, x2, y2))
        self.img = cropped.resize((200, 200))  # Resize to 200x200
        self.add_to_history()  # Add the new image state to history
        self.display_image()
        self.status_label.config(text="Cropped & resized. Click 'Save Image' to store.")

    def save_image(self):
        if self.img:
            save_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                     filetypes=[("PNG files", "*.png"),
                                                                ("JPEG files", "*.jpg"),
                                                                ("All Files", "*.*")])
            if save_path:
                self.img.save(save_path)
                self.status_label.config(text="Image saved successfully!")

    def add_to_history(self):
        """Add the current state of the image to the history stack."""
        if self.img:
            self.history.append(copy.deepcopy(self.img))  # Deep copy to preserve the current state
            self.future.clear()  # Clear future redo states

    def undo(self):
        """Undo the last action by reverting to the previous state."""
        if self.history:
            self.future.append(self.img)  # Save the current state to the redo stack
            self.img = self.history.pop()  # Revert to the last image state
            self.display_image()
            self.status_label.config(text="Undo action performed.")

    def redo(self):
        """Redo the previously undone action."""
        if self.future:
            self.history.append(self.img)  # Save current state to the undo stack
            self.img = self.future.pop()  # Restore the image from redo stack
            self.display_image()
            self.status_label.config(text="Redo action performed.")

    def resize_image(self):
        """Allow the user to resize the image."""
        if not self.img:
            self.status_label.config(text="No image to resize.")
            return
        
        # Prompt user for new width and height
        width = simpledialog.askinteger("Resize Image", "Enter new width:", minvalue=1, maxvalue=5000)
        height = simpledialog.askinteger("Resize Image", "Enter new height:", minvalue=1, maxvalue=5000)

        if width and height:
            # Resize the image
            self.img = self.img.resize((width, height))
            self.add_to_history()  # Add the new resized image state to history
            self.display_image()
            self.status_label.config(text=f"Image resized to {width}x{height}.")

    def apply_edge_detection(self):
        """Apply edge detection on the current image using OpenCV."""
        if not self.img:
            self.status_label.config(text="No image to apply edge detection.")
            return
        
        # Convert PIL Image to OpenCV format (numpy array)
        open_cv_img = np.array(self.img)
        open_cv_img = cv2.cvtColor(open_cv_img, cv2.COLOR_RGB2BGR)  # Convert to BGR (OpenCV format)

        # Apply Canny edge detection
        edges = cv2.Canny(open_cv_img, threshold1=100, threshold2=200)

        # Convert back to PIL Image
        edges_pil = Image.fromarray(edges)

        # Update the image to the edge-detected image
        self.img = edges_pil.convert("RGB")
        self.add_to_history()  # Add the new edge-detected image to history
        self.display_image()
        self.status_label.config(text="Edge detection applied.")

# Run Application
root = tk.Tk()
app = ImageCropper(root)
root.mainloop()
