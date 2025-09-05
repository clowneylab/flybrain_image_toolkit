# CMTK Image Registration - Usage Guide
- [ ] Update the documentation

Register TIF images to JRC2018 template using CMTK.

## Usage

```bash
sbatch --job-name "<job_name>" --mail-user "<your_email>" GL_warp_batch_JRC2018U.sh <input_folder> <output_folder> <reference_channel>
```

### Parameters

- `<input_folder>`: Folder containing TIF files to register
- `<output_folder>`: Where registered TIFs will be saved (created if needed)
- `<reference_channel>`: Channel number for registration (1-based, e.g., 2 for nc82)

### SLURM Options

- `--job-name`: Name for your job
- `--mail-user`: Your email for job notifications

## Example

```bash
sbatch --job-name "VPN_registration" --mail-user "yourname@umich.edu" \
  GL_warp_batch_JRC2018U.sh \
  ./data/raw_images \
  ./data/registered \
  2
```
*Clowney lab internal reference*
```bash
sbatch --job-name "Yunzhi_otp_B" --mail-user "yijiep@umich.edu" \
  GL_warp_batch_JRC2018U.sh \
  ./Yunzhi/20250723_OptixGal4,UASGFP/4-channel_ch1DAPI_ch2Otp_ch3GFP_ch4nc82 \
  ./Yunzhi/warp_output \
  4
```

## Tips

- Use nc82 channel as reference
- Check job status with `squeue -u $USER`
- Output files have `warp_` prefix
- Processing takes ~4 hours (current time limit)