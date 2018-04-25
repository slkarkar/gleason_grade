from __future__ import print_function

import tensorflow as tf
import numpy as np
import pandas as pd
from sklearn.metrics import (jaccard_similarity_score,
                             confusion_matrix,
                             roc_auc_score,
                             accuracy_score,
                             classification_report,
                             f1_score)
import os, sys, glob, shutil, time, argparse, cv2

sys.path.insert(0, '.')
from densenet import Inference

config = tf.ConfigProto()
config.gpu_options.allow_growth = True

CROP_SIZE = 1024
RESIZE_FACTOR = 0.25
XDIM = [256, 256, 3]
# SNAPSHOT = '5x/snapshots/densenet.ckpt-77345'

def compare_tile(y_true_vect, y_hat_vect):

    accuracy = accuracy_score(y_true_vect, y_hat_vect)

    return accuracy


def crop_and_resize(img, mask, crop=CROP_SIZE, resize=RESIZE_FACTOR):
    h, w = img.shape[:2]

    c_h, c_w = h/2, w/2
    crop_half = crop/2
    img = img[c_h-crop_half: c_h+crop_half, c_w-crop_half:c_w+crop_half, :]
    mask = mask[c_h-crop_half: c_h+crop_half, c_w-crop_half:c_w+crop_half]

    img = cv2.resize(img, dsize=(0,0), fx=resize, fy=resize)
    mask = cv2.resize(mask, dsize=(0,0), fx=resize, fy=resize,
        interpolation=cv2.INTER_NEAREST)

    return img, mask


def per_class_metrics(y_true_all, y_hat_all):
    unique_classes = np.unique(y_true_all)
    accuracies = []
    f1 = []
    for c in sorted(unique_classes):
        y_true_c = (y_true_all == c).astype(np.uint8)
        y_hat_c = (y_hat_all == c).astype(np.uint8)
        accuracies.append(accuracy_score(y_true_c, y_hat_c))
        f1.append(f1_score(y_true_c, y_hat_c))

    return accuracies + f1


def test_tiles(jpg_dir, mask_dir, snapshot, crop=CROP_SIZE, resize=RESIZE_FACTOR, outfile=open('result.tsv', 'a')):
    jpg_patt = os.path.join(jpg_dir, '*.jpg')
    jpg_list = sorted(glob.glob(jpg_patt))

    mask_patt = os.path.join(mask_dir, '*.png')
    mask_list = sorted(glob.glob(mask_patt))

    assert len(jpg_list) == len(mask_list)

    ## Check agreement based on filenames
    for jpg, mask in zip(jpg_list, mask_list):
        jpg_base = os.path.basename(jpg).replace('.jpg', '')
        mask_base = os.path.basename(mask).replace('.png', '')
        # print(jpg, mask)
        assert jpg_base == mask_base, '{} mismatch {}'.format(jpg, mask)
    print('Test files passed agreement check (n = {})'.format(len(jpg_list)))

    aggregate_metrics = []
    indices = []
    y_hat_all = np.array([])
    y_true_all = np.array([])
    with tf.Session(config=config) as sess:
        model = Inference(sess=sess, x_dims=XDIM)
        model.restore(snapshot)

        for idx, (jpg, mask) in enumerate(zip(jpg_list, mask_list)):
            # print('{:04d}'.format(idx), jpg, mask)
            tile_name = os.path.basename(jpg).replace('.jpg', '')
            indices.append(tile_name)
            img = cv2.imread(jpg)[:,:,::-1]
            y_true = cv2.imread(mask, -1)

            img, y_true = crop_and_resize(img, y_true)
            img = img * (2./255) - 1.

            y_hat = model.inference(np.expand_dims(img, 0))
            y_hat = np.argmax(y_hat, axis=-1)

            y_hat_vect = y_hat.flatten()
            y_true_vect = y_true.flatten()
            y_hat_all = np.concatenate([y_hat_all, y_hat_vect], axis=0)
            y_true_all = np.concatenate([y_true_all, y_true_vect], axis=0)

            aggregate_metrics.append(compare_tile(y_true_vect, y_hat_vect))

    # aggregated_metrics = pd.DataFrame(aggregate_metrics, index=indices,
    #     columns=['Accuracy'])
    # confmat = confusion_matrix(y_true_all, y_hat_all)
    # class_report = classification_report(y_true_all, y_hat_all, digits=4)
    # print(confmat)
    # print(class_report)

    metrics = per_class_metrics(y_true_all, y_hat_all)
    metric_str = ''
    for metric in metrics:
        metric_str += '{}\t'.format(metric)

    metric_str += '{}\t'.format(accuracy_score(y_true_all, y_hat_all))
    metric_str += '{}\n'.format(f1_score(y_true_all, y_hat_all, average='macro'))
    output_str = '{}\t'.format(snapshot) + metric_str
    print(output_str)
    outfile.write(output_str)
    outfile.close()


OUTPUT_HEAD = 'SNAPSHOT\tG3_A\tG4_A\tG5_A\tBN_A\tST_A\tG3_F1\tG4_F1\tG5_F1\tBN_F1\tST_F1\tOVERALL_A\tOVERALL_F1\n'
if __name__ == '__main__':
    jpg_dir = sys.argv[1]
    mask_dir = sys.argv[2]
    snapshot = sys.argv[3]
    mag = sys.argv[4]
    if mag == '5':
        crop = 1024
        resize = 0.25
    elif mag == '10':
        crop = 512
        resize = 0.5
    elif mag == '20':
        crop = 256
        resize = 1.
    else:
        print('Magnification (arg 4) invalid')
        raise Exception

    outfile = sys.argv[5]

    if not os.path.exists(outfile):
        outfile = open(outfile, 'w+')
        outfile.write(OUTPUT_HEAD)
    else:
        outfile = open(outfile, 'a')


    test_tiles(jpg_dir, mask_dir, snapshot, crop, resize, outfile)
