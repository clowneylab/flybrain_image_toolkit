
import napari
import tifffile
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import ndimage
from magicgui import magicgui
from napari.layers import Points
from napari.types import LayerDataTuple
from magicgui.widgets import Container

def calculate_region_properties(masks: np.ndarray) -> pd.DataFrame:
    """
    Calculate centroid and area for each ROI in a parallelized way.

    Args:
        masks: A numpy array of labeled masks.

    Returns:
        A pandas DataFrame with properties for each ROI.
    """
    labels = np.unique(masks)
    labels = labels[labels != 0]  # Exclude background label 0

    if labels.size == 0:
        return pd.DataFrame(columns=["label", "centroid", "area"])

    centroids = ndimage.center_of_mass(masks, masks, labels)
    areas = ndimage.sum_labels(np.ones(masks.shape), masks, labels)

    properties = [
        {"label": label, "centroid": centroid, "area": area}
        for label, centroid, area in zip(labels, centroids, areas)
    ]
    
    return pd.DataFrame(properties)

@magicgui(
    call_button="Load Image",
    image_path={"label": "Image File:", "mode": "r", "filter": "*.tif"},
)
def file_loader(viewer: napari.Viewer, image_path: Path) -> None:
    """
    A magicgui widget to load an image and associated segmentations.
    """
    viewer.layers.clear()
    
    # Load image
    image = tifffile.imread(image_path)
    viewer.add_image(
        image,
        channel_axis=1,
        name=["Ch1", "Ch2"],
        colormap=["blue", "green"],
        metadata={"image_path": image_path}
    )

    # Check for segmentation file
    segmentation_path = image_path.with_name(f"{image_path.stem}_seg.npy")
    
    good_points_data = []
    bad_points_data = []
    good_properties = {"label": [], "area": [], "status": []}
    bad_properties = {"label": [], "area": [], "status": []}

    if segmentation_path.exists():
        segmentations = np.load(segmentation_path, allow_pickle=True).item()
        masks = segmentations["masks"]
        roi_properties = calculate_region_properties(masks)

        if not roi_properties.empty:
            # Classify ROIs
            mean_area = roi_properties["area"].mean()
            std_area = roi_properties["area"].std()
            outlier_mask = (roi_properties["area"] < mean_area - 2 * std_area) | (roi_properties["area"] > mean_area + 2 * std_area)
            roi_properties["status"] = "good"
            roi_properties.loc[outlier_mask, "status"] = "bad"

            # Separate good and bad ROIs
            good_rois = roi_properties[roi_properties["status"] == "good"]
            bad_rois = roi_properties[roi_properties["status"] == "bad"]

            if not good_rois.empty:
                good_points_data = np.stack(good_rois['centroid'].values)
                good_properties = good_rois[["label", "area", "status"]].to_dict('list')

            if not bad_rois.empty:
                bad_points_data = np.stack(bad_rois['centroid'].values)
                bad_properties = bad_rois[["label", "area", "status"]].to_dict('list')

    # Add layers to viewer
    bad_points_layer = viewer.add_points(
        bad_points_data,
        properties=bad_properties,
        name='bad ROI',
        face_color='red',
        size=10,
    )
    
    good_points_layer = viewer.add_points(
        good_points_data,
        properties=good_properties,
        name='good ROI',
        face_color='white',
        size=10,
    )

    # Connect events
    good_points_layer.events.data.connect(lambda event: on_points_changed(viewer, good_points_layer))
    good_points_layer.events.data.connect(update_point_count)
    
    # Initial count update
    update_point_count()


@magicgui(auto_call=False, call_button="Save Good ROIs")
def save_widget(viewer: napari.Viewer) -> None:
    """Saves the good ROI points to a CSV file."""
    if 'good ROI' not in viewer.layers:
        print("No 'good ROI' layer found.")
        return
        
    good_points_layer = viewer.layers['good ROI']
    
    # Find the image layer and its path from metadata
    image_layer = None
    for layer in viewer.layers:
        if isinstance(layer, napari.layers.Image):
            image_layer = layer
            break

    if image_layer is None or 'image_path' not in image_layer.metadata:
        print("No image layer found or image path is missing from metadata.")
        return

    image_path = Path(image_layer.metadata['image_path'])
    save_path = image_path.with_name(f"{image_path.stem}_good_rois.csv")

    # Create a DataFrame from layer data
    properties_df = pd.DataFrame(good_points_layer.properties)
    coordinates_df = pd.DataFrame(good_points_layer.data, columns=[f"axis-{i}" for i in range(good_points_layer.data.shape[1])])
    
    # Combine coordinates and properties
    full_df = pd.concat([properties_df, coordinates_df], axis=1)
    
    full_df.to_csv(save_path, index=False)
    print(f"Saved {len(full_df)} good ROIs to {save_path}")


@magicgui(call_button=False, label_good_count={"label": "Good points count:", "enabled": True})
def count_widget(label_good_count: str = "0"):
    """A widget to display the count of good points."""
    pass

def on_points_changed(viewer: napari.Viewer, points_layer: Points):
    """
    Callback function to handle changes in the good points layer.
    Assigns properties to newly added points, handling property duplication.
    """
    num_points = len(points_layer.data)
    
    # It's safer to work with copies of the property lists
    # and ensure they are Python lists, not numpy arrays, for easier manipulation.
    properties = {k: list(v) for k, v in points_layer.properties.items()}
    
    num_properties = len(properties.get('label', []))

    # Case 1: A new point was added.
    if num_points == 1:
        print(properties)
        # This handles adding the very first point to an empty layer.
        properties['label'][-1] = 1
        properties['area'][-1] = 0
        properties['status'][-1] = "User_added"

    # Case 2: A point was added by duplicating an existing one.
    # The number of points and properties are the same, but the last label is a duplicate.
    elif num_points > 1:
        last_label = properties['label'][-1]
        # Check if the last label exists in the list of preceding labels
        if last_label in properties['label'][:-1]:
            max_label = max(properties['label'][:-1]) # Max of all labels *except* the new duplicate
            new_label = max_label + 1
            properties['label'][-1] = new_label
            properties['area'][-1] = 0
            properties['status'][-1] = "User_added"

    # Refresh properties (important for napari to see the change)
    points_layer.properties = properties


def update_point_count():
    """Updates the count of good points in the UI."""
    if 'good ROI' in viewer.layers:
        count = len(viewer.layers['good ROI'].data)
        count_widget.label_good_count.value = str(count)


if __name__ == "__main__":
    viewer = napari.Viewer()
    
    # Group widgets into a container for better layout
    container = Container(widgets=[file_loader, count_widget, save_widget], labels=False)
    viewer.window.add_dock_widget(container, area='right', name='ROI Tools')

    napari.run()
