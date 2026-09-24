# CMTK Image Averaging - Usage Guide

Normalize and average multiple registered 3D brain images (typically `.nrrd` files) into a single composite average image using the Computational Morphometry Toolkit (CMTK).

>[!TIP]
>To produce an accurate average image:
>1. All input images **must** already be registered to the same reference template (e.g., `JRC2018U` from `CMTK_rigid` or `CMTK_warp`).
>2. Input images must share identical dimensions, bounding boxes, and voxel resolutions.
>3. Averaging is performed with intensity normalization (`-n`), ensuring intensity variations across specimens do not distort the average.

---

## Usage

### SLURM Submission (U-Mich Great Lakes HPC)

Ensure the `logs/` directory exists in your working directory before submitting:
```bash
mkdir -p ./logs
```

Submit the job using `sbatch`:
```bash
sbatch --job-name "<job_name>" --mail-user "<your_email>" GL_cmtk_average.sh <output_image> <input_image_1> [input_image_2 ...]
```

### Interactive / Local Execution

If running directly in an interactive cluster shell (`salloc`) or workstation:
```bash
bash GL_cmtk_average.sh <output_image> <input_images...>
```

---

## Parameters

- `<output_image>`: Path and filename for the averaged output image (e.g., `./average_output/average_ch1.nrrd`). Parent directories are created automatically if they do not exist.
- `<input_images...>`: One or more paths to registered `.nrrd` images to be averaged. Wildcards/globs (such as `./warp_output/warp_*.nrrd`) are expanded by the shell.

### SLURM Directives

| Directive | Default in Script | Description |
| :--- | :--- | :--- |
| `--job-name` | `CMTK-average` | Descriptive job name in SLURM queue |
| `--account` | `jclowney0` | PI account for cluster allocation billing |
| `--partition` | `standard` | Queue partition (`standard`, `largemem`, `gpu`, `debug`) |
| `--nodes` / `--ntasks` | `1` / `1` | Single node, single task space |
| `--cpus-per-task` | `32` | Number of CPU cores reserved (accelerates computation) |
| `--mem` | `16g` | Total RAM reserved for the job |
| `--time` | `00:30:00` | Walltime limit (HH:MM:SS) |
| `--mail-user` | `yijiep@umich.edu` | Email address for job notifications |
| `--mail-type` | `END` | When email alerts are sent (`BEGIN`, `END`, `FAIL`, `ALL`) |
| `--output` | `./logs/%x-%j.txt` | Standard output and error log path |

---

## Examples

### 1. Submit to SLURM

Average all warped channel 1 images from a study:

```bash
mkdir -p ./logs ./data/averaged

sbatch --job-name "avg_wt_brains" \
       --mail-user "user@umich.edu" \
       --account "jclowney0" \
       GL_cmtk_average.sh \
       ./data/averaged/average_wt_ch1.nrrd \
       ./data/warped_brains/*/warp_*_ch1.nrrd
```

### 2. Run Interactively

```bash
module load cmtk/3.3.1

bash GL_cmtk_average.sh \
     ./results/composite_nc82.nrrd \
     ./registered_samples/sample1/warp_ch2.nrrd \
     ./registered_samples/sample2/warp_ch2.nrrd \
     ./registered_samples/sample3/warp_ch2.nrrd
```

---

## Under the Hood

The script invokes CMTK's `average_images` tool:
```bash
cmtk average_images -n -o <output_image> <input_image_1> <input_image_2> ...
```
- `-n`: Normalizes image intensity ranges prior to calculating voxel-wise arithmetic means.
- `-o`: Specifies the output path for the resulting `.nrrd` image.

---

## Tips & Best Practices

- **Check Job Status**: Monitor queued or running jobs with:
  ```bash
  squeue -u $USER
  ```
- **Inspect Logs**: Check log output in `./logs/CMTK-average-<JOBID>.txt`.
- **Resource Sizing**: Averaging is computationally fast compared to non-rigid registration. 16 GB RAM and 30 minutes walltime are typically sufficient for 10–30 Drosophila whole-brain standard resolution volumes.

