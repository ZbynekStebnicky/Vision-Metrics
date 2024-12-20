# Vision Metrics

**Vision Metrics** is a free, powerful, and user-friendly tool for precise image measurement and annotation. Ideal for metrology, quality control, and other image analysis tasks.

## Features

- **Distance and angle measurements** with calibration.
- **Text addition** to annotate images at precise locations.
- **Save images** with annotations for documentation and reporting.
- **Customizable colors** for lines, text, and points.
- **Intuitive pan and zoom functionality** for seamless navigation.
- **Dark mode** for better usability in low-light environments.
- Measurement history with **Undo** and **Clear All** options.
- Automatic **arc rendering** for measured angles.

## Installation

1. Clone or download the repository.
2. Navigate to the project directory.
3. Install the required Python dependencies by running:
   ```bash
   pip install -r requirements.txt

## Usage
Run the application:

  ```bash
  python VisionMetrics.py
  ```
Load an image using the **Load Image** button.

## Working with Images

1. Load an image using the **Load Image** button.
2. Select a measurement mode:
   - **Calibrate**: Define the scale by selecting two points and entering a known distance.
   - **Line**: Measure distances between two points.
   - **Angle**: Measure angles between three points.
   - **Text**: Add text annotations to specific locations on the image.
3. Customize colors, zoom, or pan as needed.
4. Save the annotated image using the **Save Image** button.

## Keyboard Shortcuts and Tips

- **Zoom**: Use the mouse scroll wheel.
- **Pan**: Hold and drag the middle mouse button.
- **Undo Last Action**: Removes the last measurement or annotation.
- **Clear Measurements**: Resets all current measurements and annotations.

## Updates

We are actively improving Vision Metrics based on user feedback.

For the latest (and potentially unstable) version, run:
```bash
python VisionMetrics_alpha.py
```

Stay tuned for more features and refinements!
