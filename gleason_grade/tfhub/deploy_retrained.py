#!/usr/bin/env python

# https://stackoverflow.com/ \
# questions/33759623/tensorflow-how-to-save-restore-a-model/47235448#47235448

from __future__ import print_function
import tensorflow as tf
import numpy as np
import os
import cv2
import sys
import glob
import time
import shutil
import argparse

# sys.path.insert(0, '..')
from svs_reader import Slide

config = tf.ConfigProto()
config.gpu_options.allow_growth = True

def preprocess_fn(img):
  img = img * (1/255.)
  return img.astype(np.float32)

def prob_output(svs):
  probs = svs.output_imgs['prob']
  probs *= 255.
  return probs.astype(np.uint8)

def transfer_to_ramdisk(src, ramdisk = '/dev/shm'):
  base = os.path.basename(src)
  dst = os.path.join(ramdisk, base)
  shutil.copyfile(src, dst)
  return dst

def get_input_output_ops(sess, model_path):
  input_key = 'image'
  output_key = 'prediction'
  print('loading model {}'.format(model_path))
  signature_key = tf.saved_model.signature_constants.default_serving_signature_def_key
  meta_graph_def = tf.saved_model.loader.load(
    sess,
    [tf.saved_model.tag_constants.serving],
    model_path )
  signature = meta_graph_def.signature_def

  print('getting tensor names:')
  image_tensor_name = signature[signature_key].inputs[input_key].name
  print('input tensor: ', image_tensor_name)
  predict_tensor_name = signature[signature_key].outputs[output_key].name
  print('output tensor:', predict_tensor_name)

  image_op = sess.graph.get_tensor_by_name(image_tensor_name)
  predict_op = sess.graph.get_tensor_by_name(predict_tensor_name)
  print('input:', image_op.get_shape())
  print('output:', predict_op.get_shape())
  return image_op, predict_op

PROCESS_MAG = 10
BATCH_SIZE = 16
OVERSAMPLE = 1.5
PRINT_ITER = 500
def main(sess, ramdisk_path, image_op, predict_op):
  input_size = image_op.get_shape().as_list()
  print(input_size)
  x_size, y_size = input_size[1:3]

  print('Working {}'.format(ramdisk_path))
  svs = Slide(slide_path  = ramdisk_path,
        preprocess_fn = preprocess_fn,
        normalize_fn  = lambda x: x, 
        process_mag   = PROCESS_MAG,
        process_size  = x_size,
        oversample_factor  = OVERSAMPLE,
        verbose = False
        )
  svs.initialize_output('prob', dim=4, mode='tile')
  PREFETCH = min(len(svs.tile_list), 1024)

  def wrapped_fn(idx):
    coords = svs.tile_list[idx]
    img = svs._read_tile(coords)
    return img, idx

  def read_region_at_index(idx):
    return tf.py_func(func = wrapped_fn,
              inp  = [idx],
              Tout = [tf.float32, tf.int64],
              stateful = False)

  ds = tf.data.Dataset.from_generator(generator=svs.generate_index,
    output_types=tf.int64)
  ds = ds.map(read_region_at_index, num_parallel_calls=8)
  ds = ds.prefetch(PREFETCH)
  ds = ds.batch(BATCH_SIZE)

  iterator = ds.make_one_shot_iterator()
  img, idx = iterator.get_next()

  print('Processing {} tiles'.format(len(svs.tile_list)))
  tstart = time.time()
  n_processed = 0
  while True:
    try:
      tile, idx_ = sess.run([img, idx])
      output = sess.run(predict_op, {image_op: tile})
      svs.place_batch(output, idx_, 'prob', mode='tile')

      n_processed += BATCH_SIZE
      if n_processed % PRINT_ITER == 0:
        print('[{:06d}] elapsed time [{:3.3f}] ({})'.format(
          n_processed, time.time() - tstart, tile.shape ))

    except tf.errors.OutOfRangeError:
      print('Finished')
      break

    except Exception as e:
      print(e.__doc__)
      print(e)
      print('Error')
      break

  dt = time.time()-tstart
  spt = dt / float(len(svs.tile_list))
  fps = len(svs.tile_list) / dt
  print('\nFinished. {:2.2f}min {:3.3f}s/tile\n'.format(dt/60., spt))
  print('\t {:3.3f} fps\n'.format(fps))

  prob_img = prob_output(svs)
  svs.close()

  return prob_img, fps


def read_list(pth):
  l = []
  with open(pth, 'r') as f:
  for L in f:
    l.append(L.strip())
  return l



if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--model_path', default='snapshots/mobilenet_v2_050_224_75pct')
  parser.add_argument('--slide_list', default='slidelist.txt')
  parser.add_argument('--out', default='cedars_inference')
  parser.add_argument('--clobber', default=False, action='store_true')

  args = parser.parse_args()
  out_dir = args.out
  print(args)

  slide_list = read_list(args.slide_list)
  print('Slide list: {}'.format(len(slide_list)))

  if not os.path.exists(out_dir):
    print('Making {}'.format(out_dir))
    os.makedirs(out_dir)

  if not args.clobber:
    processed_list = glob.glob(os.path.join(out_dir, '*_prob.npy'))
    print('Found {} processed slides.'.format(len(processed_list)))
    processed_base = [os.path.basename(x).replace('_prob.npy', '') for x in processed_list]
    slide_base = [os.path.basename(x).replace('.svs', '') for x in slide_list]
    slide_base_list = zip(slide_base, slide_list)
    slide_list = [lst for bas, lst in slide_base_list if bas not in processed_base]
    print('Trimmed processed slides. Working on {}'.format(len(slide_list)))

  print('out_dir: ', out_dir)
  with tf.Session(config=config) as sess:
    image_op , predict_op = get_input_output_ops(sess, args.model_path)
    times = {}
    fpss = {}
    for slide_num, slide_path in enumerate(slide_list):
      print('\n\n[\tSlide {}/{}\t]\n'.format(slide_num, len(slide_list)))
      ramdisk_path = transfer_to_ramdisk(slide_path)
      try:
        time_start = time.time()
        prob_img, fps = main(sess, ramdisk_path, image_op, predict_op)
        outname_prob = os.path.basename(ramdisk_path).replace('.svs', '_prob.npy')
        outpath =  os.path.join(out_dir, outname_prob)
        print('Writing {}'.format(outpath))
        np.save(outpath, prob_img)

        times[ramdisk_path] = (time.time() - time_start) / 60.
        fpss[ramdisk_path] = fps

      except Exception as e:
        print('Caught exception')
        print(e.__doc__)

      finally:
        os.remove(ramdisk_path)
        print('Removed {}'.format(ramdisk_path))

  time_record = os.path.join(out_dir, 'processing_time.txt')
  fps_record = os.path.join(out_dir, 'processing_fps.txt')
  print('Writing processing times to {}'.format(time_record))
  times_all = []
  with open(time_record, 'w+') as f:
    for slide, tt in times.items():
      times_all.append(tt)
      f.write('{}\t{:3.5f}\n'.format(slide, tt))

    times_mean = np.mean(times_all)
    times_std = np.std(times_all)
    f.write('Mean: {:3.4f} +/- {:3.5f}\n'.format(times_mean, times_std))

  fps_all = []
  print('Writing processing FPS to {}'.format(fps_record))
  with open(fps_record, 'w+') as f:
    for slide, tt in fpss.items():
      fps_all.append(tt)
      f.write('{}\t{:3.5f}\n'.format(slide, tt))

    fps_mean = np.mean(fps_all)
    fps_std = np.std(fps_all)
    f.write('Mean: {:3.4f} +/- {:3.5f}\n'.format(fps_mean, fps_std))
