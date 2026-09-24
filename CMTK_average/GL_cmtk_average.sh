#!/bin/bash
                                       ## REQUIRED: #!/bin/bash must be on the 1st line
                                       ## and it must be the only string on the line
#SBATCH --job-name=CMTK-average       ## Name of the job for the scheduler
#SBATCH --account=jclowney0            ## Your PI's uniqname plus 0,99, or other number
#SBATCH --partition=standard                ## name of the queue to submit the job to.
                                       ## Choose: standard, largemem, gpu, spgpu, debug
##SBATCH --gpus=1                                   ## if partition=gpu, number of GPUS needed
                                       ## make the directive = #SBATCH, not ##SBATCH 
#SBATCH --nodes=1                      ## number of nodes you are requesting
#SBATCH --ntasks=1                     ## how many task spaces do you want to reserve
#SBATCH --cpus-per-task=32              ## how many cores do you want to use per task
#SBATCH --time=00:30:00                ## Maximum length of time you are reserving the 
                                       ## resources for (bill is based on time used)
#SBATCH --mem=16g                      ## Total memory requested for the job
#SBATCH --mail-user=yijiep@umich.edu   ## send email notifications to umich email listed
#SBATCH --mail-type=END                ## when to send email (standard values are:
                                       ## NONE,BEGIN,END,FAIL,REQUEUE,ALL.
                                       ## (See documentation for others)
#SBATCH --output=./logs/%x-%j.txt               ## send output and error info to the file listed
                                       ##(optional: different name format than default) 

# This script is used to normalize and average registered 3D brain images using CMTK.
set -euo pipefail

# Ensure logs directory exists if running under SLURM
mkdir -p ./logs

# Validate arguments
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <output_image> <input_image1> [input_image2 ...]"
    echo "Example: bash $0 ./output/average.nrrd ./warped/warp_*.nrrd"
    exit 1
fi

# Load the necessary modules
if command -v module &> /dev/null; then
    module load cmtk/3.3.1
fi

output_image="$1"
shift
registered_images=("$@")

# Ensure output parent directory exists
mkdir -p "$(dirname "$output_image")"

echo "Averaging ${#registered_images[@]} images into: $output_image"
cmtk average_images -n -o "$output_image" "${registered_images[@]}"

echo "Averaging completed successfully."
