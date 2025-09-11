#!/bin/bash
#SBATCH --job-name=CMTK-Mask-Array
#SBATCH --account=jclowney0
#SBATCH --partition=standard
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=1:00:00
#SBATCH --mem=8g
#SBATCH --mail-user=yijiep@umich.edu
#SBATCH --mail-type=END,FAIL
#SBATCH --output=./logs/%x-%A_%a.txt

# This script is designed to be run as a SLURM job array.
# Each array task will process one .tif file from the input directory.

# Load the necessary modules
module load cmtk/3.3.1
module load fiji

# --- Input Arguments ---
# The first argument is the folder containing the .tif images
path_to_tifs=$1
output_folder=$2
reference_channel=$3

# Check if input directory is provided
if [ -z "$path_to_tifs" ]; then
    echo "Error: Please provide the path to the folder containing .tif files."
    exit 1
fi

# --- Get the specific file for this array task ---
# The SLURM_ARRAY_TASK_ID variable tells us which file to process
file=$(find "$path_to_tifs" -maxdepth 1 -type f -name "*.tif" | sed -n "${SLURM_ARRAY_TASK_ID}p")

if [ -z "$file" ]; then
    echo "Error: No file found for SLURM_ARRAY_TASK_ID: $SLURM_ARRAY_TASK_ID"
    exit 1
fi

echo "STARTING TASK $SLURM_ARRAY_TASK_ID for file: $file"

# --- Fixed Paths ---
path_to_template='./templates/JRC2018_UNISEX_38um_iso_16bit.nrrd'
path_to_macro='./macro'
path_to_label='./templates/JRC2018_ROIs/JRC2018U_central_brain_ROIs_um.nrrd'

mkdir -p $output_folder

# ----------------Preprocess the tif file----------------
echo "----------------Preprocessing $file----------------"
# create a temp folder for each tif file
temp_folder=$(basename "$file" .tif)
mkdir -p "$path_to_tifs/$temp_folder"
# convert the tif file to nrrd file
if [ ! -f "$path_to_tifs/$temp_folder/${temp_folder}_ch1.nrrd" ]; then
    fiji --headless --console -macro "$path_to_macro/splitChannel.ijm" "$file $path_to_tifs/$temp_folder/"
fi

# ----------------Registering----------------
echo "----------------Registering $file----------------"
imageBaseName=$temp_folder
path_to_images="$path_to_tifs/$temp_folder"
path_to_fixed_image="$path_to_template"
reference_image="${imageBaseName}_ch${reference_channel}.nrrd"

# start registration
if [ ! -f "$path_to_images/initial.xform" ]; then
    echo "Creating initial xform for $imageBaseName"
    cmtk make_initial_affine --principal-axes $path_to_fixed_image $path_to_images/$reference_image $path_to_images/initial.xform
    if [ $? -ne 0 ]; then echo "Error: Initial affine failed for $imageBaseName"; exit 1; fi
fi

if [ ! -d "$path_to_images/affine.xform" ]; then
    echo "Affine registration is in progress for $imageBaseName"
    cmtk registration --initial $path_to_images/initial.xform --nmi --dofs 6 --dofs 12 --nmi --exploration 16 --accuracy 0.8 --omit-original-data -o $path_to_images/affine.xform $path_to_fixed_image $path_to_images/$reference_image
    if [ $? -ne 0 ]; then echo "Error: Affine registration failed for $imageBaseName"; exit 1; fi
fi

if [ ! -d "$path_to_images/warp.xform" ]; then
    echo "Warp registration is in progress for $imageBaseName"
    cmtk warp --nmi --jacobian-weight 0 --fast -e 26 --grid-spacing 80 --energy-weight 1e-1 --refine 4 --coarsest 8 --ic-weight 0 --output-intermediate --accuracy 0.4 --omit-original-data -o $path_to_images/warp.xform $path_to_fixed_image $path_to_images/$reference_image $path_to_images/affine.xform
    if [ $? -ne 0 ]; then echo "Error: Warp registration failed for $imageBaseName"; exit 1; fi
fi
    
# reformat label
if [ ! -f "$path_to_images/Masked_$imageBaseName.nrrd" ]; then
    cmtk reformatx --interpolation nn -o "$path_to_images/Masked_$imageBaseName.nrrd" --floating $path_to_label $path_to_images/$reference_image --inverse $path_to_images/warp.xform                                                                                                          
    if [ $? -ne 0 ]; then echo "Error: Reformatx failed for Masked_$imageBaseName.nrrd"; exit 1; fi
fi

echo "----------------TASK $SLURM_ARRAY_TASK_ID for $file is done----------------"
