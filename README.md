# Flybrain_image_toolkit

A collection of tools to process Drosophila brain images. Each folder below contains a separate tool with its own documentation.

## Tools

- [cellbody_detect](cellbody_detect/README.md): Tool for detecting and counting cell bodies in Drosophila brain images. Includes a Napari ROI editor for manual annotation and review.

- [CMTK_rigid](CMTK_rigid/README.md): Batch processing scripts for rigid registration of images using CMTK, optimized for the JRC2018U template.

- [CMTK_warp](CMTK_warp/README.md): Batch processing scripts for non-rigid (warp) registration of images using CMTK, also targeting the JRC2018U template.

- [CMTK_Jacobian](CMTK_Jacobian/README.md): Performs warp registration and calculates the Jacobian determinant field.

- [VFB](VFB/download_nrrd.ipynb): Download registered nrrd images from virtual fly brain.

- [greedy_set_cover](greedy_set_cover/Najia_awasaki_clusters.ipynb): A Jupyter notebook implementing a greedy set cover algorithm to find a minimal set of transcription factors for distinguishing cell clusters.

Refer to each tool's README for usage instructions and details.
