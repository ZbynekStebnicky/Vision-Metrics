import cv2
import numpy as np
from tkinter import Tk, filedialog, Button, Canvas, Label, Frame, Radiobutton, StringVar, Entry, messagebox, colorchooser
from matplotlib.colors import to_hex
from PIL import Image, ImageTk
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

        # Sidebar controls
        Label(self.sidebar, text="Edit", font=("Arial", 12), bg="lightgray").pack(pady=10)
        Button(self.sidebar, text="Load Image", command=self.load_image, width=20).pack(pady=5)
        Button(self.sidebar, text="Clear Measurements", command=self.clear_measurements, width=20).pack(pady=5)
        Button(self.sidebar, text="Undo Last Action", command=self.undo_last_action, width=20).pack(pady=5)
        Button(self.sidebar, text="Save Image", command=self.save_image, width=20).pack(pady=5)

        Label(self.sidebar, text="Measurement Mode", bg="lightgray", font=("Arial", 12)).pack(pady=10)
        self.mode = StringVar(value="line")
        Radiobutton(self.sidebar, text="Line", variable=self.mode, value="line", bg="lightgray").pack(anchor="w", padx=20)
        Radiobutton(self.sidebar, text="Angle", variable=self.mode, value="angle", bg="lightgray").pack(anchor="w", padx=20)
        Radiobutton(self.sidebar, text="Calibrate", variable=self.mode, value="calibrate", bg="lightgray").pack(anchor="w", padx=20)

        Label(self.sidebar, text="Customize Colours", bg="lightgray", font=("Arial", 12)).pack(pady=10)
        Button(self.sidebar, text="Select Line Colour", command=self.change_line_color, width=20).pack(pady=5)
        Button(self.sidebar, text="Select Text Colour", command=self.change_text_color, width=20).pack(pady=5)
        Button(self.sidebar, text="Select Point Colour", command=self.change_point_color, width=20).pack(pady=5)

        # Canvas bindings
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<ButtonPress-2>", self.start_pan)
        self.canvas.bind("<B2-Motion>", self.do_pan)
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

    def redraw_measurements(self):
        """Redraw all measurements."""
        self.canvas.delete("measurement")

        # Draw points
        for point in self.calibration_points + self.measurement_points:
            scaled_point = self.scale_and_offset_point(point)
            self.canvas.create_oval(
                scaled_point[0] - 3, scaled_point[1] - 3,
                scaled_point[0] + 3, scaled_point[1] + 3,
                fill=self.point_color, tags="measurement"
            )

        # Draw lines
        for line in self.lines:
            start, end, distance = line
            scaled_start = self.scale_and_offset_point(start)
            scaled_end = self.scale_and_offset_point(end)
            self.canvas.create_line(
                scaled_start[0], scaled_start[1],
                scaled_end[0], scaled_end[1],
                fill=self.line_color, width=2, tags="measurement"
            )
            if distance is not None:
                midpoint = (
                    (scaled_start[0] + scaled_end[0]) // 2,
                    (scaled_start[1] + scaled_end[1]) // 2,
                )
                self.canvas.create_text(
                    midpoint[0], midpoint[1],
                    text=f"{distance:.2f} mm", fill=self.text_color,
                    font=("Arial", 10), tags="measurement"
                )

        # Draw angles
        for angle in self.angles:
            p1, p2, p3, angle_value = angle
            scaled_p1 = self.scale_and_offset_point(p1)
            scaled_p2 = self.scale_and_offset_point(p2)
            scaled_p3 = self.scale_and_offset_point(p3)
            self.canvas.create_line(
                scaled_p2[0], scaled_p2[1], scaled_p1[0], scaled_p1[1],
                fill=self.line_color, width=2, tags="measurement"
            )
            self.canvas.create_line(
                scaled_p2[0], scaled_p2[1], scaled_p3[0], scaled_p3[1],
                fill=self.line_color, width=2, tags="measurement"
            )
            self.draw_arc_with_segments(scaled_p2, scaled_p1, scaled_p3, radius=50)
            self.canvas.create_text(
                scaled_p2[0], scaled_p2[1] - 20,
                text=f"{angle_value:.2f}°", fill=self.text_color,
                font=("Arial", 10), tags="measurement"
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
            if len(self.measurement_points) == 2:
                self.draw_line()
        elif self.mode.get() == "angle" and len(self.measurement_points) < 3:
            self.measurement_points.append(point)
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
            output_image = self.image.copy()

            # Converting colors from RGB to BGR (for OpenCV)
            line_color_hex = self.color_to_hex(self.line_color)
            text_color_hex = self.color_to_hex(self.text_color)

            line_color_bgr = self.hex_to_bgr(line_color_hex)
            text_color_bgr = self.hex_to_bgr(text_color_hex)

            # Draw lines and distances
            for start, end, distance in self.lines:
                start_px = (int(start[0]), int(start[1]))
                end_px = (int(end[0]), int(end[1]))
                cv2.line(output_image, start_px, end_px, line_color_bgr, 2)
                if distance:
                    midpoint = ((start_px[0] + end_px[0]) // 2, (start_px[1] + end_px[1]) // 2)
                    cv2.putText(output_image, f"{distance:.2f} mm", midpoint, cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color_bgr, 1)

            # Draw angles and arcs
            for p1, p2, p3, angle in self.angles:
                p1_px = (int(p1[0]), int(p1[1]))
                p2_px = (int(p2[0]), int(p2[1]))
                p3_px = (int(p3[0]), int(p3[1]))
                cv2.line(output_image, p2_px, p1_px, line_color_bgr, 2)
                cv2.line(output_image, p2_px, p3_px, line_color_bgr, 2)

                # Draw the arc representing the angle
                self.draw_arc_on_image(output_image, p2_px, p1_px, p3_px, line_color_bgr)

                # Add the angle text
                text_position = (p2_px[0] + 20, p2_px[1] - 20)
                cv2.putText(output_image, f"{angle:.2f} deg", text_position, cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color_bgr, 1)

            # Save the output image
            cv2.imwrite(save_path, output_image)

    def draw_arc_on_image(self, image, center, start, end, color, thickness=2):
        """Draw an arc on the image representing an angle."""
        # Calculate angles in radians
        start_angle = atan2(start[1] - center[1], start[0] - center[0])
        end_angle = atan2(end[1] - center[1], end[0] - center[0])

        # Normalize angles to range [0, 2π)
        if start_angle < 0:
            start_angle += 2 * np.pi
        if end_angle < 0:
            end_angle += 2 * np.pi

        # Ensure the arc corresponds to the smaller angle
        angle_span = end_angle - start_angle
        if angle_span > np.pi:  # Reverse if larger than 180°
            start_angle, end_angle = end_angle, start_angle + 2 * np.pi

        # Set the radius of the arc
        radius = int(min(
            np.linalg.norm(np.array(start) - np.array(center)),
            np.linalg.norm(np.array(end) - np.array(center))
        ) * 0.2)

        # Convert angles to degrees for OpenCV
        start_angle_deg = np.degrees(start_angle)
        end_angle_deg = np.degrees(end_angle)

        # Draw the arc using OpenCV's ellipse function
        cv2.ellipse(
            image,
            center=center,
            axes=(radius, radius),
            angle=0,
            startAngle=start_angle_deg,
            endAngle=end_angle_deg,
            color=color,
            thickness=thickness
        )

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
        if self.lines:
            self.lines.pop()
        elif self.angles:
            self.angles.pop()
        elif self.calibration_points:
            self.calibration_points.pop()
        elif self.measurement_points:
            self.measurement_points.pop()
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

    def on_zoom(self, event):
        """Handle zooming."""
        scale = 1.1 if event.delta > 0 else 0.9
        self.zoom_level *= scale
        self.zoom_level = max(0.1, min(self.zoom_level, 10))  # Clamp zoom level
        self.display_image()
    
    def measure_angle(self):
        """Measure the angle between three points and draw an arc representing the angle."""
        if len(self.measurement_points) < 3:
            messagebox.showerror("Error", "Please select three points to measure an angle.")
            return

        # Extract the three points
        p1, p2, p3 = map(np.array, self.measurement_points[:3])

        # Calculate vectors
        v1 = p1 - p2
        v2 = p3 - p2

        # Calculate angle in degrees
        angle_rad = atan2(v2[1], v2[0]) - atan2(v1[1], v1[0])
        angle_deg = abs(degrees(angle_rad))
        if angle_deg > 180:
            angle_deg = 360 - angle_deg

        # Save the angle
        self.angles.append((p1.tolist(), p2.tolist(), p3.tolist(), angle_deg))

        # Scale and offset points for the canvas
        scaled_p1 = self.scale_and_offset_point(p1)
        scaled_p2 = self.scale_and_offset_point(p2)
        scaled_p3 = self.scale_and_offset_point(p3)

        # Draw the two lines forming the angle
        self.canvas.create_line(
            scaled_p2[0], scaled_p2[1], scaled_p1[0], scaled_p1[1],
            fill=self.line_color, width=2, tags="line"
        )
        self.canvas.create_line(
            scaled_p2[0], scaled_p2[1], scaled_p3[0], scaled_p3[1],
            fill=self.line_color, width=2, tags="line"
        )

        # Reset measurement points
        self.measurement_points = []
        self.redraw_measurements()

    def draw_arc_with_segments(self, center, start, end, radius=None):
        """Draw an arc explicitly as small line segments between start and end points."""
        # Adjust coordinates for angle calculations (since canvas Y increases downwards)
        start_x = start[0] - center[0]
        start_y = center[1] - start[1]  # Invert Y
        end_x = end[0] - center[0]
        end_y = center[1] - end[1]      # Invert Y

        start_angle = atan2(start_y, start_x)
        end_angle = atan2(end_y, end_x)

        # Ensure angles are in the range [0, 2*pi)
        if start_angle < 0:
            start_angle += 2 * np.pi
        if end_angle < 0:
            end_angle += 2 * np.pi

        # Ensure the arc corresponds to the smaller angle
        angle_span = end_angle - start_angle
        if angle_span > np.pi:  # If angle span is greater than 180°, reverse it
            start_angle, end_angle = end_angle, start_angle + 2 * np.pi

        # Calculate dynamic radius if not provided
        if radius is None:
            v1 = np.array([start_x, start_y])
            v2 = np.array([end_x, end_y])
            radius = int(min(np.linalg.norm(v1), np.linalg.norm(v2)) * 0.5)

        # Generate arc points
        num_segments = 200  # Higher for smoother arcs
        angles = np.linspace(start_angle, end_angle, num_segments)
        arc_points = [
            (
                int(center[0] + radius * np.cos(angle)),
                int(center[1] - radius * np.sin(angle))  # Adjust Y back to canvas coordinates
            )
            for angle in angles
        ]

        # Draw the arc as small line segments
        for i in range(len(arc_points) - 1):
            x1, y1 = arc_points[i]
            x2, y2 = arc_points[i + 1]
            self.canvas.create_line(
                x1, y1, x2, y2,
                fill=self.line_color,  # Arc line color
                width=2,
                tags="arc"
            )

    def scale_and_offset_point(self, point):
        """Scale and offset a point."""
        x = int(point[0] * self.zoom_level + self.offset_x)
        y = int(point[1] * self.zoom_level + self.offset_y)
        return x, y
    
    def draw_line(self):
        """Draw a line and calculate its distance."""
        p1, p2 = map(np.array, self.measurement_points[:2])
        pixel_distance = np.linalg.norm(p2 - p1)
        distance_mm = pixel_distance * self.scale_factor if self.scale_factor else None
        self.lines.append((p1.tolist(), p2.tolist(), distance_mm))
        self.measurement_points = []


if __name__ == "__main__":
    root = Tk()
    app = MetrologyApp(root)
    root.mainloop()