import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import tempfile

from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.fx.all import resize as mpy_resize   # MoviePy’s resize FX


class VideoEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FrameWise Video Editor")
        self.root.geometry("800x650")
        self.root.configure(bg="#ffffff")

        # ─────────── Variables ───────────
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar(value="output.mp4")
        self.start_time = tk.DoubleVar(value=0.0)
        self.end_time = tk.DoubleVar(value=0.0)

        # Separate Zoom and Resize factors
        self.zoom_factor = tk.DoubleVar(value=1.0)
        self.resize_factor = tk.DoubleVar(value=1.0)

        self.filter_type = tk.StringVar(value="none")
        self.brightness = tk.IntVar(value=0)
        self.contrast = tk.DoubleVar(value=1.0)
        self.blur_kernel = tk.IntVar(value=5)
        self.compress_level = tk.StringVar(value="Medium")
        self.video_format = tk.StringVar(value=".mp4")

        # Which operations are enabled:
        self.trim_enabled = tk.BooleanVar(value=False)
        self.zoom_enabled = tk.BooleanVar(value=False)
        self.resize_enabled = tk.BooleanVar(value=False)
        self.filter_enabled = tk.BooleanVar(value=False)
        self.adjust_enabled = tk.BooleanVar(value=False)

        self.video_duration = 0.0

        self.setup_styles()
        self.create_widgets()

    def setup_styles(self):
        primary_color = "#007acc"
        secondary_color = "#f0f0f0"
        font_main = ("Segoe UI", 10)

        self.style = ttk.Style()
        self.style.theme_use('clam')

        # “Browse” button and other specially‐styled buttons:
        self.style.configure(
            "Primary.TButton",
            font=font_main,
            padding=6,
            relief="flat",
            background=primary_color
        )
        self.style.map("Primary.TButton", background=[('active', '#005f99')])

        # Progress bar styling:
        self.style.configure(
            "Modern.Horizontal.TProgressbar",
            thickness=20,
            troughcolor=secondary_color,
            background=primary_color
        )

        # Labels, Entries, Checkbuttons:
        self.style.configure(
            "Modern.TLabel", background="white", font=font_main)
        self.style.configure("Modern.TCheckbutton",
                             background="white", font=font_main)
        self.style.configure(
            "Modern.TEntry", fieldbackground="white", bordercolor="#cccccc")

        # Notebook tabs:
        self.style.configure(
            "Modern.TNotebook.Tab",
            padding=[10, 5],
            background=secondary_color,
            foreground="black"
        )
        self.style.map("Modern.TNotebook.Tab", background=[
                       ("selected", "#e0e0e0")])

        # Hint labels (smaller, italic, gray):
        self.style.configure(
            "Hint.TLabel",
            background="white",
            font=("Segoe UI", 9, "italic"),
            foreground="#666666"
        )

    def create_widgets(self):
        notebook = ttk.Notebook(self.root, style="Modern.TNotebook")
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ─── Input Tab ───────────────────────────────────────────────────────────
        input_frame = ttk.Frame(notebook, padding=20)
        notebook.add(input_frame, text="📁 Input")
        self.build_input_tab(input_frame)

        # ─── Processing Tab ──────────────────────────────────────────────────────
        processing_frame = ttk.Frame(notebook, padding=20)
        notebook.add(processing_frame, text="⚙️ Processing")
        self.build_processing_tab(processing_frame)

        # ─── Output Tab ──────────────────────────────────────────────────────────
        output_frame = ttk.Frame(notebook, padding=20)
        notebook.add(output_frame, text="💾 Output")
        self.build_output_tab(output_frame)

        # ─── Progress Tab ────────────────────────────────────────────────────────
        progress_frame = ttk.Frame(notebook, padding=20)
        notebook.add(progress_frame, text="⏳ Progress")
        self.build_progress_tab(progress_frame)

        # “Process Video” button (default ttk style, no custom color)
        process_btn = ttk.Button(
            self.root, text="Process Video", command=self.start_processing)
        process_btn.pack(pady=15)

    # ────────────────────────────────── Input Tab ────────────────────────────────────
    def build_input_tab(self, frame):
        ttk.Label(frame, text="Input Video:",
                  style="Modern.TLabel").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.input_path, width=60,
                  style="Modern.TEntry").pack(anchor="w", pady=5)
        ttk.Button(frame, text="Browse", command=self.select_file,
                   style="Primary.TButton").pack(anchor="w", pady=5)

        ttk.Label(frame, text="Output Format:", style="Modern.TLabel").pack(
            anchor="w", pady=(15, 5))
        formats = [".mp4", ".avi", ".mkv"]
        format_menu = ttk.Combobox(
            frame, textvariable=self.video_format, values=formats, state="readonly", width=10
        )
        format_menu.pack(anchor="w")
        format_menu.bind("<<ComboboxSelected>>", self.update_output_extension)

        ttk.Label(frame, text="Output File Name:",
                  style="Modern.TLabel").pack(anchor="w", pady=(15, 5))
        ttk.Entry(frame, textvariable=self.output_path, width=60,
                  style="Modern.TEntry").pack(anchor="w")

    # ────────────────────────────── Processing Tab ─────────────────────────────────
    def build_processing_tab(self, frame):
        # --- Trim Video ---
        trim_frame = ttk.LabelFrame(frame, text="Trim Video", padding=10)
        trim_frame.pack(fill=tk.X, pady=5)

        ttk.Checkbutton(
            trim_frame,
            text="Enable Trim",
            variable=self.trim_enabled,
            command=self.toggle_trim,
            style="Modern.TCheckbutton"
        ).pack(anchor="w")

        self.start_label = ttk.Label(
            trim_frame, text="Start Time: 0.0s", style="Modern.TLabel")
        self.end_label = ttk.Label(
            trim_frame, text="End Time: 0.0s", style="Modern.TLabel")
        self.start_scale = ttk.Scale(
            trim_frame,
            from_=0.0, to=100.0,
            variable=self.start_time,
            orient=tk.HORIZONTAL,
            command=self.update_start_label,
            length=300
        )
        self.end_scale = ttk.Scale(
            trim_frame,
            from_=0.0, to=100.0,
            variable=self.end_time,
            orient=tk.HORIZONTAL,
            command=self.update_end_label,
            length=300
        )
        for widget in (self.start_label, self.start_scale, self.end_label, self.end_scale):
            widget.pack_forget()

        # --- Zoom Video (Crop) ---
        zoom_frame = ttk.LabelFrame(frame, text="Zoom (Crop)", padding=10)
        zoom_frame.pack(fill=tk.X, pady=5)

        ttk.Checkbutton(
            zoom_frame,
            text="Enable Zoom",
            variable=self.zoom_enabled,
            command=self.toggle_zoom,
            style="Modern.TCheckbutton"
        ).pack(anchor="w")

        self.zoom_label = ttk.Label(
            zoom_frame, text="Zoom Factor: 1.0×", style="Modern.TLabel")
        self.zoom_scale = ttk.Scale(
            zoom_frame,
            # can zoom out (<1) or zoom in (up to 3×)
            from_=0.1, to=3.0,
            variable=self.zoom_factor,
            orient=tk.HORIZONTAL,
            length=300,
            command=self.update_zoom_label
        )
        for widget in (self.zoom_label, self.zoom_scale):
            widget.pack_forget()

        # --- Resize Video (Upsample) ---
        resize_frame = ttk.LabelFrame(
            frame, text="Resize (Upsample)", padding=10)
        resize_frame.pack(fill=tk.X, pady=5)

        ttk.Checkbutton(
            resize_frame,
            text="Enable Resize",
            variable=self.resize_enabled,
            command=self.toggle_resize,
            style="Modern.TCheckbutton"
        ).pack(anchor="w")

        self.resize_label = ttk.Label(
            resize_frame, text="Resize Factor: 1.0×", style="Modern.TLabel")
        self.resize_scale = ttk.Scale(
            resize_frame,
            # can shrink (<1) or enlarge (up to 3×)
            from_=0.1, to=3.0,
            variable=self.resize_factor,
            orient=tk.HORIZONTAL,
            length=300,
            command=self.update_resize_label
        )
        for widget in (self.resize_label, self.resize_scale):
            widget.pack_forget()

        # --- Apply Filter ---
        filter_frame = ttk.LabelFrame(frame, text="Apply Filter", padding=10)
        filter_frame.pack(fill=tk.X, pady=5)

        ttk.Checkbutton(
            filter_frame,
            text="Enable Filter",
            variable=self.filter_enabled,
            command=self.toggle_filter,
            style="Modern.TCheckbutton"
        ).pack(anchor="w")

        ttk.Label(filter_frame, text="Filter Type:",
                  style="Modern.TLabel").pack(anchor="w", pady=(5, 0))
        self.filter_menu = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_type,
            values=["none", "gray", "blur", "edge"],
            state="readonly",
            width=10
        )
        self.filter_menu.pack(anchor="w", pady=2)
        self.filter_menu.bind("<<ComboboxSelected>>", self.filter_changed)

        self.blur_label = ttk.Label(
            filter_frame, text="Blur Kernel: 5", style="Modern.TLabel")
        self.blur_scale = ttk.Scale(
            filter_frame,
            from_=1, to=31,
            variable=self.blur_kernel,
            orient=tk.HORIZONTAL,
            length=300,
            command=self.update_blur_label
        )
        for widget in (self.blur_label, self.blur_scale):
            widget.pack_forget()

        # --- Adjust Brightness/Contrast ---
        adjust_frame = ttk.LabelFrame(
            frame, text="Adjust Brightness/Contrast", padding=10)
        adjust_frame.pack(fill=tk.X, pady=5)

        ttk.Checkbutton(
            adjust_frame,
            text="Enable Adjust",
            variable=self.adjust_enabled,
            command=self.toggle_adjust,
            style="Modern.TCheckbutton"
        ).pack(anchor="w")

        self.brightness_label = ttk.Label(
            adjust_frame, text="Brightness: 0", style="Modern.TLabel")
        self.brightness_scale = ttk.Scale(
            adjust_frame,
            from_=-100, to=100,
            variable=self.brightness,
            orient=tk.HORIZONTAL,
            length=300,
            command=self.update_brightness_label
        )
        self.contrast_label = ttk.Label(
            adjust_frame, text="Contrast: 1.0", style="Modern.TLabel")
        self.contrast_scale = ttk.Scale(
            adjust_frame,
            from_=0.0, to=3.0,
            variable=self.contrast,
            orient=tk.HORIZONTAL,
            length=300,
            command=self.update_contrast_label
        )
        for widget in (self.brightness_label, self.brightness_scale, self.contrast_label, self.contrast_scale):
            widget.pack_forget()

    # ─────────────────────────────── Output Tab ───────────────────────────────────
    def build_output_tab(self, frame):
        ttk.Label(frame, text="Compression Level:",
                  style="Modern.TLabel").pack(anchor="w")
        levels = ["Low", "Medium", "High"]
        ttk.Combobox(
            frame,
            textvariable=self.compress_level,
            values=levels,
            state="readonly",
            width=10
        ).pack(anchor="w", pady=5)

        ttk.Label(
            frame,
            text="Low = Smaller File | High = Higher Quality",
            style="Hint.TLabel"
        ).pack(anchor="w")

    # ─────────────────────────────── Progress Tab ────────────────────────────────
    def build_progress_tab(self, frame):
        self.progress = ttk.Progressbar(
            frame,
            orient="horizontal",
            length=500,
            mode="determinate",
            style="Modern.Horizontal.TProgressbar"
        )
        self.progress.pack(pady=20)

        self.status_label = ttk.Label(
            frame, text="Ready to process.", style="Modern.TLabel")
        self.status_label.pack()

    # ───────────────────────────────── Select File ────────────────────────────────
    def select_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.mp4 *.avi *.mkv")]
        )
        if file_path:
            self.input_path.set(file_path)
            try:
                clip = VideoFileClip(file_path)
                self.video_duration = clip.duration
                clip.reader.close()

                # Update sliders so they span the real duration
                self.start_scale.config(to=self.video_duration)
                self.end_scale.config(to=self.video_duration)
                self.start_time.set(0.0)
                self.end_time.set(self.video_duration)
                self.start_label.config(text=f"Start Time: 0.0s")
                self.end_label.config(
                    text=f"End Time: {self.video_duration:.1f}s")
            except Exception:
                pass

    def update_output_extension(self, *args):
        base = self.output_path.get().split(".")[0]
        self.output_path.set(f"{base}{self.video_format.get()}")

    # ─────────────────────────────────── Toggle UI ─────────────────────────────────
    def toggle_trim(self):
        widgets = [self.start_label, self.start_scale,
                   self.end_label, self.end_scale]
        if self.trim_enabled.get():
            for w in widgets:
                w.pack(anchor="w", pady=2)
        else:
            for w in widgets:
                w.pack_forget()

    def update_start_label(self, val):
        self.start_label.config(text=f"Start Time: {float(val):.1f}s")

    def update_end_label(self, val):
        self.end_label.config(text=f"End Time: {float(val):.1f}s")

    def toggle_zoom(self):
        widgets = [self.zoom_label, self.zoom_scale]
        if self.zoom_enabled.get():
            for w in widgets:
                w.pack(anchor="w", pady=2)
        else:
            for w in widgets:
                w.pack_forget()
            # Reset zoom factor display if disabled
            self.zoom_factor.set(1.0)
            self.zoom_label.config(text="Zoom Factor: 1.0×")

    def update_zoom_label(self, val):
        self.zoom_label.config(text=f"Zoom Factor: {float(val):.1f}×")

    def toggle_resize(self):
        widgets = [self.resize_label, self.resize_scale]
        if self.resize_enabled.get():
            for w in widgets:
                w.pack(anchor="w", pady=2)
        else:
            for w in widgets:
                w.pack_forget()
            # Reset resize factor display if disabled
            self.resize_factor.set(1.0)
            self.resize_label.config(text="Resize Factor: 1.0×")

    def update_resize_label(self, val):
        self.resize_label.config(text=f"Resize Factor: {float(val):.1f}×")

    def toggle_filter(self):
        if self.filter_enabled.get():
            self.filter_menu.pack(anchor="w", pady=2)
            if self.filter_type.get() == 'blur':
                self.blur_label.pack(anchor="w", pady=(5, 0))
                self.blur_scale.pack(anchor="w", pady=2)
        else:
            self.filter_menu.pack_forget()
            self.blur_label.pack_forget()
            self.blur_scale.pack_forget()

    def filter_changed(self, event):
        if self.filter_type.get() == 'blur' and self.filter_enabled.get():
            self.blur_label.pack(anchor="w", pady=(5, 0))
            self.blur_scale.pack(anchor="w", pady=2)
        else:
            self.blur_label.pack_forget()
            self.blur_scale.pack_forget()

    def update_blur_label(self, val):
        k = int(float(val))
        if k % 2 == 0:
            k += 1
            self.blur_kernel.set(k)
        self.blur_label.config(text=f"Blur Kernel: {k}")

    def toggle_adjust(self):
        widgets = [self.brightness_label, self.brightness_scale,
                   self.contrast_label, self.contrast_scale]
        if self.adjust_enabled.get():
            for w in widgets:
                w.pack(anchor="w", pady=2)
        else:
            for w in widgets:
                w.pack_forget()

    def update_brightness_label(self, val):
        self.brightness_label.config(text=f"Brightness: {int(float(val))}")

    def update_contrast_label(self, val):
        self.contrast_label.config(text=f"Contrast: {float(val):.1f}")

    # ────────────────────────────────── Start Processing ─────────────────────────────
    def start_processing(self):
        if not self.input_path.get():
            messagebox.showwarning("Warning", "Please select an input video.")
            return

        # Reset progress & status
        self.status_label.config(
            text="⏳ Processing video...", foreground="black")
        self.progress["mode"] = "determinate"
        self.progress["value"] = 0

        # Launch background thread so GUI stays responsive
        threading.Thread(target=self.process_video, daemon=True).start()

    # ────────────────────────────────── Main Processing ─────────────────────────────
    def process_video(self):
        try:
            input_video = self.input_path.get()
            output_video = self.output_path.get()
            start_time = float(self.start_time.get())
            end_time = float(self.end_time.get())
            zoom_factor = float(self.zoom_factor.get())
            resize_factor = float(self.resize_factor.get())
            filter_type = self.filter_type.get()
            brightness = int(self.brightness.get())
            contrast = float(self.contrast.get())
            blur_kernel = int(self.blur_kernel.get())

            # Map compression level → CRF and maxrate
            compress_map = {
                "Low": {"crf": "30", "maxrate": "1000k"},
                "Medium": {"crf": "26", "maxrate": "2000k"},
                "High": {"crf": "22", "maxrate": "4000k"}
            }
            compression = compress_map[self.compress_level.get()]
            crf = compression["crf"]
            maxrate = compression["maxrate"]

            # ─── 1) Open input video with OpenCV ─────────────────────────────────
            cap = cv2.VideoCapture(input_video)
            if not cap.isOpened():
                raise Exception("Cannot open video file with OpenCV.")

            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Compute final dimensions for MoviePy resize step:
            if self.resize_enabled.get():
                final_width = int(width * resize_factor)
                final_height = int(height * resize_factor)
            else:
                final_width, final_height = width, height

            # ─── 2) Create a temporary MP4 in the OS temp directory ───────────────
            temp_fd, temp_path = tempfile.mkstemp(suffix=".mp4")
            os.close(temp_fd)

            # OpenCV writes each processed frame at original (width, height).
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))

            frame_count = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                current_time = frame_count / fps

                # If trim is enabled, skip frames outside [start_time, end_time]
                if self.trim_enabled.get() and not (start_time <= current_time <= end_time):
                    frame_count += 1
                    percent = int((frame_count / total_frames) * 80)
                    self.root.after(
                        0, lambda p=percent: self.progress.config(value=p))
                    continue

                # 1) Zoom (crop) if enabled
                if self.zoom_enabled.get():
                    frame = crop_and_zoom(frame, zoom_factor)

                # 2) Apply filter if requested
                if self.filter_enabled.get() and filter_type != "none":
                    if filter_type == "gray":
                        grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        frame = cv2.cvtColor(grey, cv2.COLOR_GRAY2BGR)
                    elif filter_type == "blur":
                        k = blur_kernel
                        frame = cv2.GaussianBlur(frame, (k, k), 0)
                    elif filter_type == "edge":
                        edges = cv2.Canny(frame, 100, 200)
                        frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

                # 3) Adjust brightness/contrast if requested
                if self.adjust_enabled.get():
                    frame = cv2.convertScaleAbs(
                        frame, alpha=contrast, beta=brightness)

                # 4) Write this frame (zoomed if zoom_enabled) at original resolution
                out.write(frame)
                frame_count += 1

                # Update progress up to 80%
                percent = int((frame_count / total_frames) * 80)
                self.root.after(
                    0, lambda p=percent: self.progress.config(value=p))

            cap.release()
            out.release()

            # ─── 3) Did any frame‐by‐frame processing occur? ─────────────────────────
            did_processing = any([
                self.trim_enabled.get(),
                self.filter_enabled.get(),
                self.adjust_enabled.get(),
                self.zoom_enabled.get(),
                self.resize_enabled.get()
            ])

            if did_processing:
                # a) Grab audio (and trim if needed) from the original
                original_clip = VideoFileClip(input_video)
                if self.trim_enabled.get():
                    audio_clip = original_clip.subclip(
                        start_time, end_time).audio
                else:
                    audio_clip = original_clip.audio

                # b) Switch bar to indeterminate while MoviePy does its work
                self.root.after(
                    0, lambda: self.progress.config(mode="indeterminate"))
                self.root.after(0, lambda: self.progress.start(10))

                # c) Re‐open the temp MP4 in MoviePy
                processed_frames = VideoFileClip(temp_path)

                # d) Now upsample if resize_enabled
                if self.resize_enabled.get():
                    processed_frames = mpy_resize(
                        processed_frames, newsize=(final_width, final_height))
                # If resize wasn’t enabled, processed_frames stays at (width, height)

                # e) Attach audio
                final_clip = processed_frames.set_audio(audio_clip)

                # f) Write exactly one final file (with audio) in chosen format + CRF
                final_clip.write_videofile(
                    output_video,
                    codec="libx264",
                    audio_codec="aac",
                    ffmpeg_params=["-crf", crf, "-preset", "veryfast",
                                   "-maxrate", maxrate, "-bufsize", maxrate]
                )

                # ─── 4) Clean up MoviePy readers ───────────────────────────────
                try:
                    processed_frames.reader.close()
                    processed_frames.audio.reader.close_proc()
                    audio_clip.reader.close_proc()
                    original_clip.reader.close()
                except Exception:
                    pass

                # g) Delete the temporary file so only “output_video” remains
                if os.path.exists(temp_path):
                    os.remove(temp_path)

                # h) Switch progress bar back to determinate and fill to 100%
                self.root.after(0, lambda: self.progress.stop())
                self.root.after(
                    0, lambda: self.progress.config(mode="determinate"))
                self.root.after(0, lambda: self.progress.config(value=100))

                # i) Notify “done”
                self.root.after(0, self.show_completion)

            else:
                # No frame‐by‐frame ops: only re‐encode for compression
                clip = VideoFileClip(input_video)

                # Indeterminate while re‐encoding
                self.root.after(
                    0, lambda: self.progress.config(mode="indeterminate"))
                self.root.after(0, lambda: self.progress.start(10))

                clip.write_videofile(
                    output_video,
                    codec="libx264",
                    audio_codec="aac",
                    ffmpeg_params=["-crf", crf, "-preset", "veryfast",
                                   "-maxrate", maxrate, "-bufsize", maxrate]
                )
                try:
                    clip.reader.close()
                    clip.audio.reader.close_proc()
                except Exception:
                    pass

                # Back to determinate, fill at 100%
                self.root.after(0, lambda: self.progress.stop())
                self.root.after(
                    0, lambda: self.progress.config(mode="determinate"))
                self.root.after(0, lambda: self.progress.config(value=100))

                self.root.after(0, self.show_completion)

        except Exception as e:
            # On any exception, show error & update status
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.status_label.config(
                text="❌ Error processing video!", foreground="red"
            ))

    def show_completion(self):
        self.status_label.config(
            text="✅ Video processed successfully!", foreground="#4CAF50"
        )
        messagebox.showinfo("Success", "Processing completed!")


def crop_and_zoom(frame: np.ndarray, factor: float) -> np.ndarray:
    """
    Crop the central region of `frame` by 1/factor, then resize that crop
    back to the frame’s original width×height.

    - factor > 1.0  → zoom IN 
    - factor < 1.0  → zoom OUT (places a smaller version centered on a black canvas)
    """
    h, w = frame.shape[:2]

    if factor >= 1.0:
        # Compute size of center‐crop: (w/factor, h/factor)
        cw = int(w / factor)
        ch = int(h / factor)
        x1 = (w - cw) // 2
        y1 = (h - ch) // 2
        cropped = frame[y1: y1 + ch, x1: x1 + cw]
        # Scale that crop back to full (w, h)
        return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

    else:
        # factor < 1.0 → “zoom out.” Shrink the entire frame to (w*factor, h*factor),
        # then place it centered on a black background of size (w, h).
        nw = int(w * factor)
        nh = int(h * factor)
        if nw < 1 or nh < 1:
            # Avoid zero‐dimension
            return np.zeros_like(frame)

        small = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
        canvas = np.zeros_like(frame)
        x_offset = (w - nw) // 2
        y_offset = (h - nh) // 2
        canvas[y_offset: y_offset + nh, x_offset: x_offset + nw] = small
        return canvas


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoEditorApp(root)
    root.mainloop()
