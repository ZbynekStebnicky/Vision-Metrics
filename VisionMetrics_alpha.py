import cv2
import numpy as np
from tkinter import Tk, filedialog, Button, Canvas, Label, Frame, Radiobutton, StringVar, Entry, messagebox, colorchooser, Checkbutton, IntVar, Listbox
from matplotlib.colors import to_hex
from PIL import Image, ImageTk, ImageFont, ImageDraw
from math import atan2, degrees

class MetrologyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Vision Metrics")

        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Set window dimensions
        window_width = 1700
        window_height = 900

        # Calculate position to center the window
        position_x = (screen_width - window_width) // 2
        position_y = (screen_height - window_height) // 2

        # Set the window size and position
        self.root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")

        # Default parameters
        self.line_color = "blue"
        self.text_color = "yellow"
        self.point_color = "red"

        self.zoom_level = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.start_x = None
        self.start_y = None

        # Image and measurement variables
        self.image = None
        self.image_tk = None
        self.scale_factor = None
        self.calibration_points = []
        self.measurement_points = []
        self.lines = []
        self.angles = []
        self.drawn_items = []
        self.arcs = []  # New list to track drawn arcs
        self.arc_lines = []
        self.action_stack = []  # Stack to track actions for undo
        self.measurement_history = []
        self.is_dark_mode = False

        # Setup GUI
        self.setup_gui()

    def setup_gui(self):
        """Setup the graphical user interface."""
        # Sidebar
        self.sidebar = Frame(self.root, width=300, bg="lightgray")
        self.sidebar.pack(side="left", fill="y")

        # Canvas
        self.canvas = Canvas(self.root, bg="gray")
        self.canvas.pack(side="right", padx=10, pady=10, expand=True, fill="both")
        self.canvas.bind("<Motion>", self.on_mouse_motion)

        # Sidebar controls
        Label(self.sidebar, text="Edit", font=("Arial", 12), bg="lightgray").pack(pady=5)
        Button(self.sidebar, text="Load Image", command=self.load_image, width=20).pack(pady=5)
        Button(self.sidebar, text="Clear Measurements", command=self.clear_measurements, width=20).pack(pady=5)
        Button(self.sidebar, text="Undo Last Action", command=self.undo_last_action, width=20).pack(pady=5)
        Button(self.sidebar, text="Save Image", command=self.save_image, width=20).pack(pady=5)
        Button(self.sidebar, text="Toggle Dark Mode", command=self.toggle_dark_mode, width=20).pack(pady=5)

        Label(self.sidebar, text="Measurement Mode", bg="lightgray", font=("Arial", 12)).pack(pady=5)
        self.mode = StringVar(value="line")
        Radiobutton(self.sidebar, text="Line", variable=self.mode, value="line", bg="lightgray").pack(anchor="w", padx=20)
        Radiobutton(self.sidebar, text="Angle", variable=self.mode, value="angle", bg="lightgray").pack(anchor="w", padx=20)
        Radiobutton(self.sidebar, text="Calibrate", variable=self.mode, value="calibrate", bg="lightgray").pack(anchor="w", padx=20)

        Label(self.sidebar, text="Layer Management", bg="lightgray", font=("Arial", 12)).pack(pady=5)
        self.show_lines_var = IntVar(value=1)
        self.show_points_var = IntVar(value=1)
        self.show_angles_var = IntVar(value=1)
        Checkbutton(self.sidebar, text="Show Lines", variable=self.show_lines_var, command=self.redraw_measurements).pack(anchor="w")
        Checkbutton(self.sidebar, text="Show Points", variable=self.show_points_var, command=self.redraw_measurements).pack(anchor="w")
        Checkbutton(self.sidebar, text="Show Angles", variable=self.show_angles_var, command=self.redraw_measurements).pack(anchor="w")

        Label(self.sidebar, text="Zoom Level", bg="lightgray", font=("Arial", 12)).pack(pady=5)
        self.zoom_label = Label(self.sidebar, text="Zoom: 100%", bg="lightgray")
        self.zoom_label.pack()
        Button(self.sidebar, text="Reset View", command=self.reset_view, width=20).pack(pady=5)

        Label(self.sidebar, text="Customize Colours", bg="lightgray", font=("Arial", 12)).pack(pady=5)
        Button(self.sidebar, text="Select Line Colour", command=self.change_line_color, width=20).pack(pady=5)
        Button(self.sidebar, text="Select Text Colour", command=self.change_text_color, width=20).pack(pady=5)
        Button(self.sidebar, text="Select Point Colour", command=self.change_point_color, width=20).pack(pady=5)

        Label(self.sidebar, text="Measurement History", bg="lightgray", font=("Arial", 12)).pack(pady=5)
        self.history_listbox = Listbox(self.sidebar, height=10)
        self.history_listbox.pack(pady=5)

        # Canvas bindings
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<ButtonPress-2>", self.start_pan)
        self.canvas.bind("<B2-Motion>", self.do_pan)
        self.canvas.bind("<ButtonRelease-2>", self.stop_pan)
        self.canvas.bind("<Button-1>", self.on_click)

    def load_image(self):
        """Load an image and display it on the canvas."""
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.png;*.jpeg;*.bmp")])
        if file_path:
            self.image = cv2.imread(file_path)
            self.zoom_level = 1.0
            self.offset_x = 0
            self.offset_y = 0
            self.scale_factor = None  # Reset calibration
            self.display_image()

    def add_tooltip(self, x, y, text):
        """Display a tooltip at the specified location with the given text."""
        self.tooltip = self.canvas.create_text(
            x + 10, y + 10,  # Offset tooltip for better visibility
            text=text, fill="yellow", font=("Arial", 10), tags="tooltip", anchor="nw"
        )
        # Automatically hide the tooltip after 2 seconds
        self.canvas.after(1000, lambda: self.canvas.delete("tooltip"))

    def display_image(self):
        """Display the image on the canvas."""
        if self.image is not None:
            height, width, _ = self.image.shape
            new_width = int(width * self.zoom_level)
            new_height = int(height * self.zoom_level)
            resized_image = cv2.resize(self.image, (new_width, new_height))

            # Convert to RGB and create Tk-compatible image
            image_rgb = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image_rgb)
            self.image_tk = ImageTk.PhotoImage(pil_image)

            # Clear canvas and redraw image
            self.canvas.delete("all")
            self.canvas.create_image(self.offset_x, self.offset_y, anchor="nw", image=self.image_tk, tags="image")
            self.redraw_measurements()

    def toggle_dark_mode(self):
        """Toggle between light and dark modes."""
        self.is_dark_mode = not self.is_dark_mode
        bg_color = "black" if self.is_dark_mode else "lightgray"
        text_color = "white" if self.is_dark_mode else "black"
        textus_color = "gray" if self.is_dark_mode else "black"

        # Update sidebar background and text colors
        self.sidebar.configure(bg=bg_color)
        for widget in self.sidebar.winfo_children():
            widget_type = widget.winfo_class()
            if widget_type in ["Label", "Button", "Listbox"]:
                widget.configure(bg=bg_color, fg=text_color)
            elif widget_type in ["Checkbutton", "Radiobutton"]:
                widget.configure(bg=bg_color, fg=textus_color)

        # Update canvas background
        self.canvas.configure(bg="black" if self.is_dark_mode else "gray")

    def reset_view(self):
        self.zoom_level = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.zoom_label.config(text="Zoom: 100%")  # Update the zoom label
        self.display_image()

    def add_to_history(self, measurement):
        """Add a measurement to the history listbox."""
        if measurement["type"] == "point":
            self.history_listbox.insert("end", f"Point: ({measurement['x']}, {measurement['y']})")
        elif measurement["type"] == "line":
            self.history_listbox.insert("end", f"Line: ({measurement['x1']}, {measurement['y1']}) -> ({measurement['x2']}, {measurement['y2']})")
        elif measurement["type"] == "angle":
            self.history_listbox.insert("end", f"Angle: ({measurement['points']}) -> {measurement['angle']}°")

    def redraw_measurements(self):
        """Redraw all measurements."""
        self.canvas.delete("measurement")

        # Redraw points if enabled
        if self.show_points_var.get():
            for i, point in enumerate(self.calibration_points + self.measurement_points):
                scaled_point = self.scale_and_offset_point(point)
                self.canvas.create_oval(
                    scaled_point[0] - 3, scaled_point[1] - 3,
                    scaled_point[0] + 3, scaled_point[1] + 3,
                    fill=self.point_color, tags=(f"point_{i}", "measurement")
                )

        # Redraw lines if enabled
        if self.show_lines_var.get():
            for i, (start, end, distance) in enumerate(self.lines):
                scaled_start = self.scale_and_offset_point(start)
                scaled_end = self.scale_and_offset_point(end)
                line_tag = f"line_{i}"
                self.canvas.create_line(
                    scaled_start[0], scaled_start[1],
                    scaled_end[0], scaled_end[1],
                    fill=self.line_color, width=2, tags=(line_tag, "measurement")
                )
                if distance is not None:  # Add distance text
                    midpoint = (
                        (scaled_start[0] + scaled_end[0]) // 2,
                        (scaled_start[1] + scaled_end[1]) // 2
                    )
                    self.canvas.create_text(
                        midpoint[0], midpoint[1],
                        text=f"{distance:.2f} mm", fill=self.text_color,
                        font=("Arial", 10), tags=(f"text_{line_tag}", "measurement")
                    )
                    # Attach distance to tooltip
                    self.canvas.tag_bind(line_tag, "<Enter>", lambda e, d=distance: self.add_tooltip(e.x, e.y, f"Distance: {d:.2f} mm"))

        # Redraw angles if enabled
        if self.show_angles_var.get():
            for i, (p1, p2, p3, angle_value) in enumerate(self.angles):
                scaled_p1 = self.scale_and_offset_point(p1)
                scaled_p2 = self.scale_and_offset_point(p2)
                scaled_p3 = self.scale_and_offset_point(p3)

                angle_tag = f"angle_{i}"
                # Draw angle lines
                self.canvas.create_line(
                    scaled_p2[0], scaled_p2[1], scaled_p1[0], scaled_p1[1],
                    fill=self.line_color, width=2, tags=(angle_tag, "measurement")
                )
                self.canvas.create_line(
                    scaled_p2[0], scaled_p2[1], scaled_p3[0], scaled_p3[1],
                    fill=self.line_color, width=2, tags=(angle_tag, "measurement")
                )
                # Draw the arc
                self.draw_arc_with_segments(scaled_p2, scaled_p1, scaled_p3, radius=50)
                # Attach angle to tooltip
                self.canvas.tag_bind(angle_tag, "<Enter>", lambda e, a=angle_value: self.add_tooltip(e.x, e.y, f"Angle: {a:.2f}°"))

                # Display angle value
                self.canvas.create_text(
                    scaled_p2[0], scaled_p2[1] - 20,
                    text=f"{angle_value:.2f}°", fill=self.text_color,
                    font=("Arial", 10), tags=(f"text_{angle_tag}", "measurement")
                )

    def add_to_history(self, measurement):
        """Add a measurement to the history listbox."""
        if measurement["type"] == "point":
            self.history_listbox.insert("end", f"Point: ({measurement['x']:.2f}, {measurement['y']:.2f})")
        elif measurement["type"] == "line":
            self.history_listbox.insert(
                "end", f"Line: ({measurement['x1']:.2f}, {measurement['y1']:.2f}) -> ({measurement['x2']:.2f}, {measurement['y2']:.2f})"
            )
        elif measurement["type"] == "angle":
            self.history_listbox.insert(
                "end", f"Angle: {measurement['angle']:.2f}° between {measurement['points']}"
            )

    def on_click(self, event):
        """Handle clicks for adding points."""
        point = [(event.x - self.offset_x) / self.zoom_level, (event.y - self.offset_y) / self.zoom_level]
        if self.mode.get() == "calibrate":
            self.calibration_points.append(point)
            if len(self.calibration_points) == 2:
                self.calibrate()
        elif self.mode.get() == "line" and len(self.measurement_points) < 2:
            self.measurement_points.append(point)
            self.add_to_history({"type": "point", "x": point[0], "y": point[1]})
            self.action_stack.append({
                                        'type': 'point',
                                        'data': point
                                    })
            if len(self.measurement_points) == 2:
                self.draw_line()
        elif self.mode.get() == "angle" and len(self.measurement_points) < 3:
            self.measurement_points.append(point)
            self.action_stack.append({
                                        'type': 'point',
                                        'data': point
                                    })
            if len(self.measurement_points) == 3:
                self.measure_angle()
        self.redraw_measurements()

    def calibrate(self):
        """Set the scale factor using two calibration points."""
        if len(self.calibration_points) != 2:
            messagebox.showwarning("Calibration Error", "Please select exactly two points for calibration.")
            return
        p1, p2 = map(np.array, self.calibration_points)
        pixel_distance = np.linalg.norm(p2 - p1)
        if pixel_distance == 0:
            messagebox.showerror("Error", "Points must not overlap.")
            return
        top = Tk()
        top.title("Calibration")
        Label(top, text="Enter the known distance (in mm):").pack(pady=10)
        calibration_entry = Entry(top)
        calibration_entry.pack(pady=10)

        def set_scale():
            try:
                known_distance = float(calibration_entry.get())
                self.scale_factor = known_distance / pixel_distance
                self.calibration_points.clear()
                self.action_stack.append({
                                            'type': 'calibration',
                                            'previous_points': self.calibration_points[:],
                                            'previous_scale': self.scale_factor
                                        })
                top.destroy()
                messagebox.showinfo("Calibration Success", f"Scale factor set to {self.scale_factor:.4f} mm/pixel.")
            except ValueError:
                messagebox.showerror("Error", "Invalid input. Enter a numeric value.")

        Button(top, text="Set Scale", command=set_scale).pack(pady=10)

    def color_to_hex(self, color):
        """Convert a color name or hex value to hex format (#RRGGBB)."""
        try:
            return to_hex(color, keep_alpha=False)
        except ValueError:
            raise ValueError(f"Invalid color: {color}")

    def hex_to_bgr(self, hex_color):
        """Convert hex color (#RRGGBB) to BGR tuple for OpenCV."""
        if not hex_color.startswith('#') or len(hex_color) != 7:
            raise ValueError(f"Invalid hex color format: {hex_color}")
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (4, 2, 0))

    def save_image(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if save_path and self.image is not None:
            # Create a copy of the image in RGB format for PIL
            output_image = cv2.cvtColor(self.image.copy(), cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(output_image)
            draw = ImageDraw.Draw(pil_image)

            # Load a font with degree symbol support
            font_path = "arial.ttf"  # Update this path to the correct font file location on your system
            font = ImageFont.truetype(font_path, size=20)

            # Draw lines and distances
            for start, end, distance in self.lines:
                start_px = (int(start[0]), int(start[1]))
                end_px = (int(end[0]), int(end[1]))
                draw.line([start_px, end_px], fill=self.line_color, width=2)
                if distance:
                    midpoint = ((start_px[0] + end_px[0]) // 2, (start_px[1] + end_px[1]) // 2)
                    draw.text(midpoint, f"{distance:.2f} mm", fill=self.text_color, font=font)

            # Draw angles and arcs
            for p1, p2, p3, angle in self.angles:
                p1_px = (int(p1[0]), int(p1[1]))
                p2_px = (int(p2[0]), int(p2[1]))
                p3_px = (int(p3[0]), int(p3[1]))
                draw.line([p2_px, p1_px], fill=self.line_color, width=2)
                draw.line([p2_px, p3_px], fill=self.line_color, width=2)

                # Draw the arc representing the angle
                self.draw_arc_on_image(pil_image, p2_px, p1_px, p3_px)

                # Add the angle text with a degree symbol
                text_position = (p2_px[0] + 20, p2_px[1] - 20)
                draw.text(text_position, f"{angle:.2f}°", fill=self.text_color, font=font)

            # Convert back to OpenCV format (BGR) and save
            output_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            cv2.imwrite(save_path, output_image)

    def draw_arc_on_image(self, image, center, start, end, thickness=1):
        """Draw an arc representing the smaller angle on the image."""
        # Calculate angles in radians
        start_angle = atan2(start[1] - center[1], start[0] - center[0])
        end_angle = atan2(end[1] - center[1], end[0] - center[0])

        # Normalize angles to range [0, 2π)
        if start_angle < 0:
            start_angle += 2 * np.pi
        if end_angle < 0:
            end_angle += 2 * np.pi

        # Calculate the angle span and ensure it corresponds to the smaller arc
        angle_span = end_angle - start_angle
        if angle_span < 0:
            angle_span += 2 * np.pi
        if angle_span > np.pi:
            start_angle, end_angle = end_angle, start_angle
            angle_span = 2 * np.pi - angle_span

        # Set the radius of the arc
        radius = int(min(
            np.linalg.norm(np.array(start) - np.array(center)),
            np.linalg.norm(np.array(end) - np.array(center))
        ) * 0.25)

        # Convert angles to degrees for Pillow
        start_angle_deg = np.degrees(start_angle)
        end_angle_deg = np.degrees(end_angle)

        # Draw the arc using Pillow's drawing functionality
        draw = ImageDraw.Draw(image)
        bbox = [
            (center[0] - radius, center[1] - radius),
            (center[0] + radius, center[1] + radius)
        ]
        draw.arc(bbox, start=start_angle_deg, end=end_angle_deg, fill=self.line_color, width=thickness)

    def change_line_color(self):
        """Change the line color."""
        color_code = colorchooser.askcolor(title="Choose Line Color")[1]
        if color_code:
            self.line_color = color_code
            self.redraw_measurements()

    def change_text_color(self):
        """Change the text color."""
        color_code = colorchooser.askcolor(title="Choose Text Color")[1]
        if color_code:
            self.text_color = color_code
            self.redraw_measurements()

    def change_point_color(self):
        """Change the point color."""
        color_code = colorchooser.askcolor(title="Choose Point Color")[1]
        if color_code:
            self.point_color = color_code
            self.redraw_measurements()

    def undo_last_action(self):
        """Undo the last action."""
        if not self.action_stack:
            messagebox.showinfo("Undo", "Nothing to undo!")
            return

        # Pop the last action from the stack
        last_action = self.action_stack.pop()
        action_type = last_action['type']

        try:
            if action_type == 'line' and self.lines:
                # Remove the last line
                self.lines.pop()
                if len(self.action_stack) >= 2:  # Ensure there are enough items to pop
                    self.action_stack.pop()
                    self.action_stack.pop()
            elif action_type == 'angle' and self.angles:
                # Remove the last angle and its associated arcs
                self.angles.pop()
                if self.arcs:
                    last_arc = self.arcs.pop()  # Get the last arc group
                    for segment in last_arc:
                        self.canvas.delete(segment)  # Remove each segment of the arc
                if len(self.action_stack) >= 3:  # Ensure there are enough items to pop
                    self.action_stack.pop()
                    self.action_stack.pop()
                    self.action_stack.pop()
            elif action_type == 'calibration':
                # Restore the previous calibration state
                self.calibration_points = last_action.get('previous_points', [])
                self.scale_factor = last_action.get('previous_scale', None)
            else:
                messagebox.showwarning("Undo Error", f"Unknown action type: {action_type}")
        except Exception as e:
            messagebox.showerror("Undo Error", f"An error occurred while undoing: {str(e)}")

        # Redraw the canvas to reflect the undone state
        self.redraw_measurements()

    def clear_measurements(self):
        """Clear all measurements."""
        self.canvas.delete("all")
        self.display_image()
        self.calibration_points.clear()
        self.measurement_points.clear()
        self.lines.clear()
        self.angles.clear()
        self.drawn_items.clear()

    def start_pan(self, event):
        """Start panning."""
        self.start_x = event.x
        self.start_y = event.y
        self.canvas.config(cursor="fleur")  # Change cursor to a grabbing hand

    def do_pan(self, event):
        """Handle panning."""
        if self.start_x is not None and self.start_y is not None:
            dx = event.x - self.start_x
            dy = event.y - self.start_y
            self.offset_x += dx
            self.offset_y += dy
            self.start_x = event.x
            self.start_y = event.y
            self.display_image()
    
    def stop_pan(self, event):
        """Stop panning and reset cursor."""
        self.start_x = None
        self.start_y = None
        self.canvas.config(cursor="arrow")  # Reset cursor to default

    def on_zoom(self, event):
        """Handle zooming."""
        scale = 1.1 if event.delta > 0 else 0.9
        self.zoom_level *= scale
        self.zoom_level = max(0.1, min(self.zoom_level, 10))  # Clamp zoom level
        self.zoom_label.config(text=f"Zoom: {int(self.zoom_level * 100)}%")
        self.display_image()
    
    def measure_angle(self):
        """Measure the angle between three points and draw an arc representing the angle."""
        if len(self.measurement_points) < 3:
            messagebox.showerror("Error", "Please select three points to measure an angle.")
            return

        # Extract the three points
        p1, p2, p3 = map(np.array, self.measurement_points[:3])

        # Calculate vectors and angle
        v1 = p1 - p2
        v2 = p3 - p2
        angle_rad = atan2(v2[1], v2[0]) - atan2(v1[1], v1[0])
        angle_deg = abs(degrees(angle_rad))
        if angle_deg > 180:
            angle_deg = 360 - angle_deg

        # Save the angle
        angle = (p1.tolist(), p2.tolist(), p3.tolist(), angle_deg)
        self.angles.append(angle)
        self.add_to_history({"type": "angle", "points": [p1.tolist(), p2.tolist(), p3.tolist()], "angle": angle_deg})

        # Draw the arc
        arc_segments = self.draw_arc_with_segments(
            self.scale_and_offset_point(p2), self.scale_and_offset_point(p1),
            self.scale_and_offset_point(p3), radius=50
        )

        # Record this action for undo
        self.action_stack.append({
            'type': 'angle',
            'angle': angle,
            'arc': arc_segments,
            'points': [p1.tolist(), p2.tolist(), p3.tolist()]  # Points associated with this angle
        })

        # Clear measurement points after adding the angle
        self.measurement_points = []
        self.redraw_measurements()

    def draw_arc_with_segments(self, center, start, end, radius=None):
        """Draw an arc explicitly as small line segments between start and end points."""
        start_x = start[0] - center[0]
        start_y = center[1] - start[1]  # Invert Y
        end_x = end[0] - center[0]
        end_y = center[1] - end[1]      # Invert Y

        start_angle = atan2(start_y, start_x)
        end_angle = atan2(end_y, end_x)

        # Normalize angles to range [0, 2π)
        if start_angle < 0:
            start_angle += 2 * np.pi
        if end_angle < 0:
            end_angle += 2 * np.pi

        angle_span = end_angle - start_angle
        if angle_span > np.pi:
            start_angle, end_angle = end_angle, start_angle + 2 * np.pi

        if radius is None:
            v1 = np.array([start_x, start_y])
            v2 = np.array([end_x, end_y])
            radius = int(min(np.linalg.norm(v1), np.linalg.norm(v2)) * 0.5)

        num_segments = 200
        angles = np.linspace(start_angle, end_angle, num_segments)
        arc_points = [
            (
                int(center[0] + radius * np.cos(angle)),
                int(center[1] - radius * np.sin(angle))
            )
            for angle in angles
        ]

        arc_segments = []
        for i in range(len(arc_points) - 1):
            x1, y1 = arc_points[i]
            x2, y2 = arc_points[i + 1]
            arc_segment = self.canvas.create_line(
                x1, y1, x2, y2,
                fill=self.line_color,
                width=2,
                tags="measurement"
            )
            arc_segments.append(arc_segment)

        # Save arc segments as a group
        self.arcs.append(arc_segments)

    def scale_and_offset_point(self, point):
        """Scale and offset a point."""
        x = int(point[0] * self.zoom_level + self.offset_x)
        y = int(point[1] * self.zoom_level + self.offset_y)
        return x, y
    
    def draw_line(self):
        """Draw a line and calculate its distance."""
        # Ensure there are exactly two points
        if len(self.measurement_points) != 2:
            messagebox.showerror("Error", "Please select two points to draw a line.")
            return

        # Extract the two points
        p1, p2 = map(np.array, self.measurement_points[:2])

        # Calculate the pixel distance
        pixel_distance = np.linalg.norm(p2 - p1)

        # Handle zero-length line
        if pixel_distance == 0:
            messagebox.showerror("Error", "The two points are identical. Cannot draw a line.")
            return

        # Convert to real-world distance if calibrated
        distance_mm = pixel_distance * self.scale_factor if self.scale_factor else None

        # Notify user if uncalibrated
        if self.scale_factor is None:
            messagebox.showinfo("Notice", "The line distance is approximate as the system is not calibrated.")

        # Save the line data
        line = (p1.tolist(), p2.tolist(), distance_mm)
        self.lines.append(line)

        # Add to history with distance
        self.add_to_history({"type": "line", "x1": p1[0], "y1": p1[1], "x2": p2[0], "y2": p2[1], "distance_mm": distance_mm})

        # Record for undo functionality
        self.action_stack.append({
            'type': 'line',
            'line': line,
            'points': [p1.tolist(), p2.tolist()]  # Points associated with this line
        })

        # Clear measurement points after adding the line
        self.measurement_points = []

        # Redraw the canvas
        self.redraw_measurements()

    def on_mouse_motion(self, event):
        """Change cursor dynamically based on mode."""
        mode_cursor = {
            "calibrate": "plus",
            "line": "cross",
            "angle": "circle"
        }
        self.canvas.config(cursor=mode_cursor.get(self.mode.get(), "arrow"))


if __name__ == "__main__":
    root = Tk()
    app = MetrologyApp(root)
    root.mainloop()