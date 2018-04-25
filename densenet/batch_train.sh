#!/bin/bash

set -e

# batch_sizes=(32 16 4)
# img_ratios=(0.25 0.5 1.0)
# basedirs=('5x' '10x' '20x')

batch_sizes=(24 10 4)
img_ratios=(0.25 0.5 1.0)
crop_sizes=(512 512 512)
epochs=(100 100 100)
basedirs=('5x' '10x' '20x')

for i in `seq 0 2`; do
  python ./train.py ${batch_sizes[$i]} ${img_ratios[$i]} ${crop_sizes[$i]} ${epochs[$i]} ${basedirs[$i]}
done
