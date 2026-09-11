
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

# =============================================================================
# Upstream Napari Bug Fixes / Monkey-Patches for 3D Points Layer
# =============================================================================
# Bug 1: TypeError: unsupported operand type(s) for -: 'NoneType' and 'int'
# In Points.remove_selected, self._value_stored can be None when deleting points
# while hovering over a point. Ensure _value_stored is an integer before deletion.
_orig_remove_selected = Points.remove_selected

def _safe_remove_selected(self):
    if getattr(self, '_value_stored', None) is None:
        self._value_stored = getattr(self, '_value', 0)
        if self._value_stored is None:
            self._value_stored = 0
    try:
        return _orig_remove_selected(self)
    except TypeError as e:
        if "NoneType" in str(e):
            self._value_stored = 0
            return _orig_remove_selected(self)
        raise

Points.remove_selected = _safe_remove_selected

# Bug 2: IndexError in Points._indices_view setter
# When deleting points in 3D, in-flight slice requests can return indices computed
# before points were removed. Napari evaluates self.shown[value] which throws
# IndexError if value contains stale indices >= len(self.shown).
_orig_indices_view_prop = Points._indices_view

def _safe_indices_view_setter(self, value):
    if value is not None and len(value) > 0:
        value = np.asarray(value, dtype=int)
        max_len = len(getattr(self, 'shown', []))
        if max_len > 0:
            value = value[value < max_len]
        elif max_len == 0:
            value = np.empty(0, dtype=int)
    return _orig_indices_view_prop.fset(self, value)

Points._indices_view = _orig_indices_view_prop.setter(_safe_indices_view_setter)

# Bug 3: Defensive guard for Points._view_size
_orig_view_size_prop = getattr(Points, '_view_size', None)
if _orig_view_size_prop is not None and hasattr(_orig_view_size_prop, 'fget'):
    def _safe_view_size(self):
        try:
            return _orig_view_size_prop.fget(self)
        except IndexError:
            max_len = len(getattr(self, 'size', []))
            if max_len > 0:
                indices = getattr(self, '_indices_view', [])
                if len(indices) > 0:
                    valid = indices < max_len
                    if not np.all(valid):
                        self._indices_view = indices[valid]
                        return _orig_view_size_prop.fget(self)
            return np.array([])

    Points._view_size = property(_safe_view_size, _orig_view_size_prop.fset)


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

    # Configure feature defaults for points added interactively
    default_props = {'label': 0, 'area': 0, 'status': 'User_added'}
    try:
        good_points_layer.feature_defaults = default_props
    except Exception:
        pass
    try:
        good_points_layer.current_properties = default_props
    except Exception:
        pass

    # Connect events
    good_points_layer.events.data.connect(update_point_count)
    
    # Initial count update
    update_point_count()


@magicgui(
    call_button="Load Good ROIs",
    roi_file={"label": "Good ROI CSV:", "mode": "r", "filter": "*.csv"},
)
def load_roi_widget(viewer: napari.Viewer, roi_file: Path) -> None:
    """
    A magicgui widget to load previously saved good ROI points from a CSV file
    and overwrite the current 'good ROI' layer.
    """
    if not roi_file or not roi_file.exists() or not roi_file.is_file():
        print("Please select a valid CSV file.")
        return

    try:
        df = pd.read_csv(roi_file)
    except Exception as e:
        print(f"Failed to read CSV file {roi_file}: {e}")
        return

    # Identify coordinate columns (e.g. axis-0, axis-1, axis-2, or z, y, x)
    coord_cols = [c for c in df.columns if c.startswith("axis-")]
    if coord_cols:
        coord_cols.sort(key=lambda c: int(c.split("-")[1]))
    elif all(c in df.columns for c in ["z", "y", "x"]):
        coord_cols = ["z", "y", "x"]
    elif all(c in df.columns for c in ["y", "x"]):
        coord_cols = ["y", "x"]
    else:
        print(f"No valid coordinate columns found in {roi_file}. Expected 'axis-0', 'axis-1', ...")
        return

    points_data = df[coord_cols].to_numpy()
    n_pts = len(points_data)

    # Reconstruct properties with sanitization
    properties = {}
    if "label" in df.columns:
        labels = pd.to_numeric(df["label"], errors='coerce')
        next_lbl = 1
        clean_labels = []
        for v in labels:
            if pd.isna(v) or v <= 0:
                clean_labels.append(next_lbl)
                next_lbl += 1
            else:
                clean_labels.append(int(v))
                next_lbl = max(next_lbl, int(v) + 1)
        properties["label"] = clean_labels
    else:
        properties["label"] = list(range(1, n_pts + 1))

    if "area" in df.columns:
        properties["area"] = pd.to_numeric(df["area"], errors='coerce').fillna(0).tolist()
    else:
        properties["area"] = [0] * n_pts

    if "status" in df.columns:
        properties["status"] = df["status"].fillna("User_added").astype(str).tolist()
    else:
        properties["status"] = ["User_added"] * n_pts

    # Reconstruct visual attributes with strict validation against NaN / invalid values
    kwargs = {
        'name': 'good ROI',
        'size': 10,
        'face_color': 'white',
    }
    if "point_size" in df.columns:
        clean_sizes = pd.to_numeric(df["point_size"], errors='coerce').fillna(10.0).to_numpy()
        clean_sizes[clean_sizes <= 0] = 10.0
        kwargs['size'] = clean_sizes

    if "face_color" in df.columns:
        clean_colors = []
        for c in df["face_color"]:
            if pd.isna(c) or str(c).lower().strip() in ('nan', '', 'none'):
                clean_colors.append('#FFFFFFFF')
            else:
                clean_colors.append(str(c).strip())
        kwargs['face_color'] = clean_colors

    if "symbol" in df.columns:
        clean_symbols = []
        for s in df["symbol"]:
            s_str = str(s).lower().strip() if pd.notna(s) else 'disc'
            if s_str in ('nan', '', 'none', 'null'):
                s_str = 'disc'
            clean_symbols.append(s_str)
        kwargs['symbol'] = clean_symbols

    # Remove existing 'good ROI' layer if present to avoid event desync during replacement
    if 'good ROI' in viewer.layers:
        viewer.layers.remove('good ROI')

    good_points_layer = viewer.add_points(
        points_data,
        properties=properties,
        **kwargs
    )

    # Configure feature defaults for points added interactively
    default_props = {'label': 0, 'area': 0, 'status': 'User_added'}
    try:
        good_points_layer.feature_defaults = default_props
    except Exception:
        pass
    try:
        good_points_layer.current_properties = default_props
    except Exception:
        pass

    # Connect events
    good_points_layer.events.data.connect(update_point_count)

    # Update point count widget
    update_point_count()
    print(f"Loaded {len(points_data)} good ROIs from {roi_file}")


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

    n_points = len(good_points_layer.data)
    if n_points == 0:
        print("No points in 'good ROI' layer to save.")
        return

    # Create a DataFrame from layer data
    properties_df = pd.DataFrame(good_points_layer.properties)

    # Ensure required columns exist
    if 'label' not in properties_df.columns:
        properties_df['label'] = 0
    if 'area' not in properties_df.columns:
        properties_df['area'] = 0
    if 'status' not in properties_df.columns:
        properties_df['status'] = 'good'

    properties_df['area'] = properties_df['area'].fillna(0)
    properties_df['status'] = properties_df['status'].fillna('User_added')

    # Assign unique incremented labels to user-added points or unassigned labels
    existing_labels = set()
    for val in properties_df['label']:
        if pd.notna(val) and isinstance(val, (int, float, np.number)) and int(val) > 0:
            existing_labels.add(int(val))

    next_label = max(existing_labels, default=0) + 1
    seen_labels = set()
    for idx in properties_df.index:
        val = properties_df.at[idx, 'label']
        is_invalid = pd.isna(val) or not isinstance(val, (int, float, np.number)) or int(val) <= 0 or int(val) in seen_labels
        if is_invalid:
            properties_df.at[idx, 'label'] = next_label
            seen_labels.add(next_label)
            next_label += 1
            if properties_df.at[idx, 'status'] == 'good':
                properties_df.at[idx, 'status'] = 'User_added'
        else:
            seen_labels.add(int(val))

    # Re-index properties_df to match n_points exactly
    properties_df = properties_df.iloc[:n_points].reset_index(drop=True)
    coordinates_df = pd.DataFrame(good_points_layer.data, columns=[f"axis-{i}" for i in range(good_points_layer.data.shape[1])]).reset_index(drop=True)

    # Collect per-point visual attributes guaranteed to match n_points length
    # Point sizes (napari stores a 2-D array of shape [N, ndim]; take the first column)
    sizes = good_points_layer.size
    if sizes.ndim > 1:
        sizes = sizes[:, 0]
    if len(sizes) != n_points:
        sizes = np.resize(sizes, n_points) if len(sizes) > 0 else np.full(n_points, 10.0)
    point_size_series = pd.Series(sizes, name="point_size", index=range(n_points)).fillna(10.0)

    # Symbols: good_points_layer.symbol can be a single string (e.g. 'disc') or an array of symbols
    raw_symbol = good_points_layer.symbol
    if isinstance(raw_symbol, str):
        symbols = [raw_symbol] * n_points
    elif isinstance(raw_symbol, (list, np.ndarray)) and len(raw_symbol) == n_points:
        symbols = [str(s) if pd.notna(s) and str(s).lower() not in ('nan', '', 'none') else 'disc' for s in raw_symbol]
    else:
        try:
            symbols = [str(s) for s in raw_symbol]
            if len(symbols) != n_points:
                symbols = (symbols + ['disc'] * n_points)[:n_points]
        except Exception:
            symbols = ['disc'] * n_points
    symbol_series = pd.Series(symbols, name="symbol", index=range(n_points)).fillna('disc')

    # Face colors (RGBA float array → hex string for readability)
    face_colors_rgba = good_points_layer.face_color  # shape [N, 4]
    def rgba_to_hex(rgba):
        try:
            r, g, b, a = (int(round(c * 255)) for c in rgba)
            return f"#{r:02X}{g:02X}{b:02X}{a:02X}"
        except Exception:
            return "#FFFFFFFF"

    if len(face_colors_rgba) == n_points:
        face_color_hex = [rgba_to_hex(row) for row in face_colors_rgba]
    else:
        face_color_hex = ['#FFFFFFFF'] * n_points
    face_color_series = pd.Series(face_color_hex, name="face_color", index=range(n_points)).fillna('#FFFFFFFF')

    # Combine coordinates, properties, and visual attributes
    full_df = pd.concat(
        [properties_df, coordinates_df, point_size_series, symbol_series, face_color_series],
        axis=1,
    )
    
    full_df.to_csv(save_path, index=False)
    print(f"Saved {len(full_df)} good ROIs to {save_path}")


@magicgui(call_button=False, label_good_count={"label": "Good points count:", "enabled": True})
def count_widget(label_good_count: str = "0"):
    """A widget to display the count of good points."""
    pass


def update_point_count():
    """Updates the count of good points in the UI."""
    if 'good ROI' in viewer.layers:
        count = len(viewer.layers['good ROI'].data)
        count_widget.label_good_count.value = str(count)
    else:
        count_widget.label_good_count.value = "0"


if __name__ == "__main__":
    viewer = napari.Viewer()
    
    # Group widgets into a container for better layout
    container = Container(widgets=[file_loader, load_roi_widget, count_widget, save_widget], labels=False)
    viewer.window.add_dock_widget(container, area='right', name='ROI Tools')

    napari.run()
