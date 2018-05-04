#!/bin/bash

set -e

svs_dir=/media/nathan/d5fd9c1c-4512-4133-a14c-0eada5531282/slide_data/CEDARS_PRAD
svslist=$( ls /media/nathan/d5fd9c1c-4512-4133-a14c-0eada5531282/slide_data/CEDARS_PRAD/*svs )
model_name=inception_v3
outdir="inference/$model_name"
model_path="snapshots/$model_name"

# for svs in ${svslist[@]}; do
#   echo $svs $outdir
#   python ./deploy_retrained.py --model_path $model_path --slide $svs --out $outdir
# done

ls $svs_dir/*svs | shuf | parallel --jobs 2 "python deploy_retrained.py --model_path=$model_path --out=$outdir --slide={}"
