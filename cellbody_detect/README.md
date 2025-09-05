# Napari ROI Editor

This is a simple Napari-based application for loading, visualizing, and editing Regions of Interest (ROIs) from image segmentation results. It allows users to manually curate ROIs, classifying them as "good" or "bad", and save the results.

## Setup

Follow these steps to set up a Conda environment and install the necessary dependencies to run the script.

### 1. Create a Conda Environment

It is recommended to create a new Conda environment to keep the dependencies for this project isolated.

Open your terminal and run the following command to create an environment named `napari-env` with Python 3.9:

```bash
conda create -n napari-env python=3.9
```

Once the environment is created, activate it:

```bash
conda activate napari-env
```

### 2. Install Dependencies

With the Conda environment activated, install the required Python packages using `pip`:

```bash
pip install "napari[all]" tifffile pandas scipy
```

This command installs:
- `napari`: The core application and all its GUI backends.
- `tifffile`: For reading `.tif` image files.
- `pandas`: For data manipulation and saving CSV files.
- `scipy`: Used for the optimized calculation of ROI properties.

## Workflow

### 1. Run the Application

Navigate to the directory containing the `napari_roi_editor.py` script in your terminal and run the following command:

```bash
python napari_roi_editor.py
```

This will launch the Napari viewer with the custom ROI Tools widget docked on the right.

### 2. Load an Image

- Click the **"Load Image"** button in the "ROI Tools" widget.
- Browse and select a `.tif` image file.
- The application will then perform the following actions:
    - The multichannel image is loaded and displayed.
    - It automatically looks for a corresponding segmentation file in the same directory (e.g., `my_image_seg.npy` for `my_image.tif`).
    - If a segmentation file is found, it calculates the properties of each ROI and classifies them as "good" or "bad" based on their area.
    - Two point layers are created:
        - `good ROI`: White points representing valid ROIs.
        - `bad ROI`: Red points representing outlier ROIs.

### 3. Edit ROIs

- You can manually add or remove points from the **`good ROI`** layer.
- To do this, select the `good ROI` layer in the layer list (at the bottom left).
- Use the point editing tools from the napari toolbar (on the left) to add new points or delete existing ones.
- When you add a new point, it will automatically be assigned a new unique label and a status of "User_added".
- The **"Good points count"** display will update automatically as you edit the points.

### 4. Save Results

- Once you are satisfied with your edits, click the **"Save Good ROIs"** button.
- This will save the coordinates and properties of all points currently in the `good ROI` layer to a CSV file.
- The file will be saved in the same directory as the original image with the suffix `_good_rois.csv` (e.g., `my_image_good_rois.csv`).

## Expected File Structure

For the automatic loading of segmentations to work, your files should be named as follows:

- Image File: `your_image_name.tif`
- Segmentation File: `your_image_name_seg.npy`

The segmentation `.npy` file is expected to be a pickled dictionary containing at least a key `"masks"`, where the value is a NumPy array of labeled regions.
