#!/bin/bash
                                       ## REQUIRED: #!/bin/bash must be on the 1st line
                                       ## and it must be the only string on the line
#SBATCH --job-name=CMTK-rigid       ## Name of the job for the scheduler
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
#SBATCH --mem=48g                      ## Memory requested per core
#SBATCH --mail-user=yijiep@umich.edu   ## send email notifications to umich email listed
#SBATCH --mail-type=END                ## when to send email (standard values are:
                                       ## NONE,BEGIN,END,FAIL,REQUEUE,ALL.
                                       ## (See documentation for others)
#SBATCH --output=./logs/%x-%j.txt               ## send output and error info to the file listed
                                       ##(optional: different name format than default) 

# Load the necessary modules
module load cmtk/3.3.1
module load fiji

path_to_tifs=$1 #'./Yijie/KC_manipulation' #the folder for tif images need to be registered 
path_to_template='./templates/JRC2018_UNISEX_38um_iso_16bit.nrrd' # template
path_to_macro='./macro' #path to macro folder
output_folder=$2 #'./Yijie/output' # output folder, will create one if needed
reference_channel=$3 # reference channel for registration

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
        # cmtk make_initial_affine $path_to_template $path_to_images/$reference_image $path_to_images/initial.xform
        # cmtk make_initial_affine --centers-of-mass $path_to_template $path_to_images/$reference_image $path_to_images/initial.xform
        if [ $? -ne 0 ]; then
            echo "Error: Initial affine transformation failed for $imageBaseName"
            exit 1
        fi
    fi

    if [ ! -d "$path_to_images/rigid.xform" ]; then
        echo "Rigid registration is in progress for $image_name"
        # cmtk registration --initial $path_to_images/initial.xform --nmi --dofs 6,6,6,6 --exploration 16 --accuracy 0.8 -o $path_to_images/rigid.xform $path_to_template $path_to_images/$reference_image
        cmtk registration --initial $path_to_images/initial.xform --auto-multi-levels 3 -s 0.5 --nmi --exploration 16 --accuracy 0.4 -o $path_to_images/rigid.xform $path_to_template $path_to_images/$reference_image
        if [ $? -ne 0 ]; then
            echo "Error: Rigid registration failed for $imageBaseName"
            exit 1
        fi
    fi

    for image in $nrrd_list; do
        channel_basename=$(basename "$image")
        # # example channel_basename:YP-24-045_Male4_ch1.nrrd
        # channel_number=$(echo $channel_basename | grep -oP 'ch\d+' | grep -oP '\d+')
        rigid_basename="rigid_$channel_basename"
        # # only reformating the channels specified in reformat_channels
        # if [[ ! " ${reformat_channels[@]} " =~ " ${channel_number} " ]]; then
        #     continue
        # fi
        # register all channels
        if [ ! -f "$path_to_images/$rigid_basename" ]; then
            cmtk reformatx -v --pad-out 0 --target-grid "1052,900,270:0.38,0.38,1:114,0,0" -o $path_to_images/$rigid_basename --floating $image $path_to_images/rigid.xform
            #cmtk reformatx -v --pad-out 0 -o $path_to_images/$rigid_basename --floating $image $path_to_template $path_to_images/rigid.xform
            if [ $? -ne 0 ]; then
                echo "Error: Reformatx failed for $imageBaseName"
                exit 1
            fi
        fi
        echo "Reformat is done for $rigid_basename"
    done

    # ----------------Aggregate the registered images----------------
    echo "----------------Aggregating $file----------------"

    #aggregate the registered images
    rigid_image_list=$(find "$path_to_images" -maxdepth 1 -name "rigid_*.nrrd")
    echo $rigid_image_list
    fiji --headless --console -macro "$path_to_macro/mergeChannel.ijm" "$rigid_image_list"
    mv "rigid_$imageBaseName.tif" "$output_folder/rigid_$imageBaseName.tif"
    #rm -r "$temp_folder"
    # let's keep everything for now
    echo "----------------$file is done----------------"

done