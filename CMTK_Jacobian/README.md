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
