# CMTK Warp Registration and Jacobian - Usage Guide

Performs warp registration on TIF images to the JRC2018 template and calculates the Jacobian determinant field using CMTK.

>[!TIP]
>To correctly register TIF images, they need to meet the following requirements:
>1. They must contain at least a complete central brain.
>2. The images should be taken from anterior to posterior.
>3. The brain should be oriented within ±80º.
>4. The images must have at least one neuropile channel, such as brp or synapsin, for accurate registration.

## Usage

```bash
sbatch --job-name "<job_name>" --mail-user "<your_email>" GL_batch_warp_Jacobian_JRC2018U.sh <input_folder> <output_folder> <reference_channel>
```

### Parameters

- `<input_folder>`: Folder containing TIF files to register.
- `<output_folder>`: Where the output files will be saved (created if needed).
- `<reference_channel>`: Channel number to use for registration (1-based, e.g., 2 for nc82).

### SLURM Options

- `--job-name`: A descriptive name for your SLURM job.
- `--mail-user`: Your email address to receive job status notifications.

## Example

```bash
sbatch --job-name "Jacobian_calc" --mail-user "yourname@umich.edu" \
  GL_batch_warp_Jacobian_JRC2018U.sh \
  ./data/raw_images \
  ./data/jacobian_output \
  4
```

## Output

This script produces two main types of output files inside a temporary folder for each input image:

- `warp_*.nrrd`: The reference channel image after warp registration.
- `jacobian_*.nrrd`: The Jacobian determinant field, representing local volume changes.

## Tips

- Use a clear neuropile channel (like nc82) as the reference for best results.
- Monitor your job's progress with `squeue`.
- The default time limit is set to 10 hours per job.

## Apply Brain Mask to Original Image Space

This script uses the generated registration to transform a standard brain mask back into the coordinate space of the original, un-registered image. This is useful for isolating the brain region in the raw data. It is designed to be run as a SLURM job array, processing one image per task.

### Usage

First, count the number of `.tif` files in your input directory, then submit the job array.

```bash
# Count the number of .tif files
NUM_FILES=$(ls -1q <input_folder>/*.tif | wc -l)

# Submit the job array
sbatch --array=1-$NUM_FILES --job-name "<job_name>" --mail-user "<your_email>" GL_batch_mask_JRC2018U_array.sh <input_folder> <output_folder> <reference_channel>
```

### Parameters

- `<input_folder>`: Folder containing the TIF files that were registered.
- `<output_folder>`: Where the output mask files will be saved.
- `<reference_channel>`: Channel number that was used for registration (1-based).

### Example

```bash
# Count the files
NUM_FILES=$(ls -1q ./data/raw_images/*.tif | wc -l)

# Submit the job
sbatch --array=1-$NUM_FILES --job-name "Masking" --mail-user "yourname@umich.edu" \
  GL_batch_mask_JRC2018U_array.sh \
  ./data/raw_images \
  ./data/masked_output \
  4
```

### Output

- `Masked_*.nrrd`: The brain mask transformed into the space of the original input image, located in the temporary folder for each image.
