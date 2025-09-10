#!/bin/bash
                                       ## REQUIRED: #!/bin/bash must be on the 1st line
                                       ## and it must be the only string on the line
#SBATCH --job-name=CMTK-Jacobian      ## Name of the job for the scheduler
#SBATCH --account=jclowney0            ## Your PI's uniqname plus 0,99, or other number
#SBATCH --partition=standard                ## name of the queue to submit the job to.
                                       ## Choose: standard, largemem, gpu, spgpu, debug
##SBATCH --gpus=1                                   ## if partition=gpu, number of GPUS needed
                                       ## make the directive = #SBATCH, not ##SBATCH 
#SBATCH --nodes=1                      ## number of nodes you are requesting
#SBATCH --ntasks=1                     ## how many task spaces do you want to reserve
#SBATCH --cpus-per-task=32              ## how many cores do you want to use per task
#SBATCH --time=10:00:00                ## Maximum length of time you are reserving the 
                                       ## resources for (bill is based on time used)
#SBATCH --mem=24g                      ## Memory requested per core
#SBATCH --mail-user=yijiep@umich.edu   ## send email notifications to umich email listed
#SBATCH --mail-type=END                ## when to send email (standard values are:
                                       ## NONE,BEGIN,END,FAIL,REQUEUE,ALL.
                                       ## (See documentation for others)
#SBATCH --output=./logs/%x-%j.txt               ## send output and error info to the file listed
                                       ##(optional: different name format than default) 


# Load the necessary modules
module load cmtk/3.3.1
module load fiji

# Input arguments
path_to_tifs=$1 # folder for tif images to be registered
output_folder=$2 # output folder, will create one if needed
reference_channel=$3 # reference channel for registration

# Fixed template and macro folder (edit if needed)
path_to_template='./templates/JRC2018_UNISEX_38um_iso_16bit.nrrd'
path_to_macro='./macro'

mkdir -p $output_folder

# find all the tif files in the folder
find "$path_to_tifs" -maxdepth 1 -type f -name "*.tif" | while read -r file; do
    # ----------------Preprocess the tif files----------------
    echo "----------------Preprocessing $file----------------"
    # create a temp folder to each tif file
    temp_folder=$(basename "$file" .tif)
    mkdir -p "$path_to_tifs/$temp_folder"
    # convert the tif file to nrrd file
    if [ ! -f "$path_to_tifs/$temp_folder/${temp_folder}_ch1.nrrd" ]; then
        fiji --headless --console -macro "$path_to_macro/splitChannel.ijm" "$file $path_to_tifs/$temp_folder/"
    fi
    # find the nrrd files in the temp folder
    nrrd_list=$(find "$path_to_tifs/$temp_folder" -maxdepth 1 -type f -name "*.nrrd" ! -name "rigid_*.nrrd")
    echo $nrrd_list


    # ----------------Registering----------------
    # start registration
    echo "----------------Registering $file----------------"
    imageBaseName=$temp_folder
    path_to_images="$path_to_tifs/$temp_folder"
    path_to_fixed_image="$path_to_template"

    reference_image="${imageBaseName}_ch${reference_channel}.nrrd"

    # start registration
    if [ ! -f "$path_to_images/initial.xform" ]; then
        echo "Creating initial xform for $imageBaseName"
        cmtk make_initial_affine --principal-axes $path_to_template $path_to_images/$reference_image $path_to_images/initial.xform
        if [ $? -ne 0 ]; then
            echo "Error: Initial affine transformation failed for $imageBaseName"
            exit 1
        fi
    fi

    if [ ! -d "$path_to_images/affine.xform" ]; then
        echo "Affine registration is in progress for $image_name"
        cmtk registration --initial $path_to_images/initial.xform --nmi --dofs 6 --dofs 12 --nmi --exploration 16 --accuracy 0.8 --omit-original-data -o $path_to_images/affine.xform $path_to_template $path_to_images/$reference_image
        if [ $? -ne 0 ]; then
            echo "Error: Affine registration failed for $imageBaseName"
            exit 1
        fi
    fi

    if [ ! -d "$path_to_images/warp.xform" ]; then
        echo "Warp registration is in progress for $image_name"
        cmtk warp --nmi --jacobian-weight 0 --fast -e 26 --grid-spacing 80 --energy-weight 1e-1 --refine 4 --coarsest 8 --ic-weight 0 --output-intermediate --accuracy 0.4 --omit-original-data -o $path_to_images/warp.xform $path_to_template $path_to_images/$reference_image $path_to_images/affine.xform
        if [ $? -ne 0 ]; then
            echo "Error: Warp registration failed for $imageBaseName"
            exit 1
        fi
    fi

    # reformat reference channel
    warped_basename=warp_${imageBaseName}_ch${reference_channel}.nrrd
    if [ ! -f "$path_to_images/$warped_basename" ]; then
        cmtk reformatx -v --pad-out 0 -o $path_to_images/$warped_basename --target-grid "1210,566,174:0.52,0.52,1:0,0,0" --floating $path_to_images/$reference_image $path_to_images/warp.xform
        if [ $? -ne 0 ]; then
            echo "Error: Reformat failed for $imageBaseName"
            exit 1
        fi
    fi

    # reformat jacobian
    jacobian_basename=jacobian_${imageBaseName}.nrrd
    if [ ! -f "$path_to_images/$jacobian_basename" ]; then
        cmtk reformatx -v -o $path_to_images/$jacobian_basename $path_to_images/$warped_basename --jacobian --inverse $path_to_images/warp.xform
        if [ $? -ne 0 ]; then
            echo "Error: Jacobian reformat failed for $imageBaseName"
            exit 1
        fi
    fi
    echo "Jacobian reformat is done for $jacobian_basename"
done
echo "----------------$file is done----------------"
