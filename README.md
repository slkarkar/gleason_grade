# Gleason Grade

This project contains the code to train, test, and deploy semantic segmentation models.
The training data may be available by request.

If you find this code useful please cite:

```
bibtex
```

Original | Classified
:-------:|:---------:
<img src="./assets/1305474_rgb.jpg" width="512"> | <img src="./assets/1305474_classified.jpg" width="512">

### Installation

Scripts may be run from the root directory of this project, or from any of the sub-directories.
Most of the scripts rely on our `tfmodels` package for CNN models, or `svs_reader` package for efficient and extensible reading of SVS format whole slide images.

```
pip install numpy opencv-contrib-python openslide-python tensorflow-gpu pandas
git clone https://github.com/BioImageInformatics/gleason_grade
cd gleason_grade
git clone https://github.com/BioImageInformatics/svs_reader
git clone https://github.com/BioImageInformatics/tfmodels
```

Tested on Ubuntu. Python 2.7 and 3.6


### Tutorials

1. Creating data from image / mask pairs
2. Training a segmentation network using `tfmodels`
3. Validating performance on image / mask pairs
4. Applying the model to a whole slide `svs` image



### Directory structure
---
```
gleason_grade/
|__ data/
    |__ train_jpg (1)
    |__ train_mask (2)
    |__ save_tfrecord.py (3)
    |__ ...misc utility scripts...
|__ densenet/ (4)
    |__ densenet.py (5)
    |__ train.py (6)
    |__ test.py (7)
    |__ experiment_name/ (8)
	|__ logs/ (8a)
	|__ snapshots/ (8b)
	|__ inference/ (8c)
	|__ debug/ (8d)
    ...
|__ densenet_small/
    ...
|__ fcn8s/
...
|__ notebooks/ (9)
|__ tfhub/ (10)
    |__ create_tfhub_training.py (11)
    |__ retrain.py (12)
    |__ deploy_retrained.py (13)
    |__ test_retrained.py (14)
    |__ run_retrain.sh (15)
    |__ run_deploy.sh (16)

```
1. A directory with source training images
2. A directory with source training masks, **name matched to (1)**
3. Utility for translating (1) and (2) into `tfrecord` format for training
4. Model directory. Each model gets its own directory for organizing snapshots and results.
5. The model definition file. This extends one of the base classes in `tfmodels`
6. Training script. Each model directory has a copy.
7. Testing script. Each model directory has a copy.
8. By default the trained models populate a folder with the structure:
	- **a** tensorflow logs for visualization via `tensorboard`
	- **b** model snapshots for restoring
	- **c** placeholder for inference outputs generated by this model
	- **d** placeholder for misc debugging output -- images, masks, etc.
9. A set of jupyter notebooks for running various experiments, and collecting results. Notably, `colorize_numpy.ipynb` will read the output files in a given directory and produce a color-coded png based on a given color scheme.
10. [Tensorflow HUB](https://www.tensorflow.org/hub/) experiments.
11. Translate images in (1) and (2) into labelled tiles for classifier trainig
12. The retraining script from `tensorflow/examples/image_retraining`
13. Script to apply retrained Hub modules to SVS files
14. Run a test on retrained Hub classifiers
15. Utility script to hold options for retraining
16. Utility script to hold options for deploy


### Notebooks
