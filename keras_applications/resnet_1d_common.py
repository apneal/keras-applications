"""ResNet, ResNetV2, and ResNeXt models for Keras.

# Reference papers

- [Deep Residual Learning for Image Recognition]
  (https://arxiv.org/abs/1512.03385) (CVPR 2016 Best Paper Award)
- [Identity Mappings in Deep Residual Networks]
  (https://arxiv.org/abs/1603.05027) (ECCV 2016)
- [Aggregated Residual Transformations for Deep Neural Networks]
  (https://arxiv.org/abs/1611.05431) (CVPR 2017)

# Reference implementations

- [TensorNets]
  (https://github.com/taehoonlee/tensornets/blob/master/tensornets/resnets.py)
- [Caffe ResNet]
  (https://github.com/KaimingHe/deep-residual-networks/tree/master/prototxt)
- [Torch ResNetV2]
  (https://github.com/facebook/fb.resnet.torch/blob/master/models/preresnet.lua)
- [Torch ResNeXt]
  (https://github.com/facebookresearch/ResNeXt/blob/master/models/resnext.lua)
- [Torch ResNet18 and ResNet34]
  (https://github.com/pytorch/vision/blob/master/torchvision/models/resnet.py)
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import numpy as np
import tensorflow as tf

from keras_applications import get_submodules_from_kwargs
from keras_applications import imagenet_utils
from keras_applications.imagenet_utils import decode_predictions
from keras_applications.imagenet_utils import _obtain_input_shape_1d


backend = None
layers = None
models = None
utils = None


def block0(x, filters, kernel_size=3, stride=1,
           conv_shortcut=True, kernel_initializer='he_uniform', name=None):
    """A residual block.

    # Arguments
        x: input tensor.
        filters: integer, filters of the bottleneck layer.
        kernel_size: default 3, kernel size of the bottleneck layer.
        stride: default 1, stride of the first layer.
        conv_shortcut: default True, use convolution shortcut if True,
            otherwise identity shortcut.
        name: string, block label.

    # Returns
        Output tensor for the residual block.
    """
    bn_axis = 2 if backend.image_data_format() == 'channels_last' else 1

    if conv_shortcut is True:
        shortcut = layers.Conv1D(filters, 1, strides=stride, padding='SAME', kernel_initializer=kernel_initializer,
                                 name=name + '_0_conv')(x)
        shortcut = layers.BatchNormalization(axis=bn_axis, epsilon=1.001e-5,
                                             name=name + '_0_bn')(shortcut)
    else:
        shortcut = x

    x = layers.Conv1D(filters, kernel_size, strides=stride, padding='SAME', kernel_initializer=kernel_initializer,
                      name=name + '_1_conv')(x)
    x = layers.BatchNormalization(axis=bn_axis, epsilon=1.001e-5,
                                  name=name + '_1_bn')(x)
    x = layers.Activation('relu', name=name + '_1_relu')(x)

    x = layers.Conv1D(filters, kernel_size, padding='SAME', kernel_initializer=kernel_initializer,
                      name=name + '_2_conv')(x)
    x = layers.BatchNormalization(axis=bn_axis, epsilon=1.001e-5,
                                  name=name + '_2_bn')(x)

    x = layers.Add(name=name + '_add')([shortcut, x])
    x = layers.Activation('relu', name=name + '_out')(x)
    return x


def stack0(x, filters, blocks, stride1=2, kernel_initializer='he_uniform', name=None):
    """A set of stacked residual blocks.

    # Arguments
        x: input tensor.
        filters: integer, filters of the bottleneck layer in a block.
        blocks: integer, blocks in the stacked blocks.
        stride1: default 2, stride of the first layer in the first block.
        name: string, stack label.

    # Returns
        Output tensor for the stacked blocks.
    """
    x = block0(x, filters, stride=stride1, kernel_initializer=kernel_initializer, name=name + '_block1')
    for i in range(2, blocks + 1):
        x = block0(x, filters, conv_shortcut=False, kernel_initializer=kernel_initializer, name=name + '_block' + str(i))
    return x


def block1(x, filters, kernel_size=3, stride=1, kernel_initializer='he_uniform',
           conv_shortcut=True, name=None):
    """A residual block.

    # Arguments
        x: input tensor.
        filters: integer, filters of the bottleneck layer.
        kernel_size: default 3, kernel size of the bottleneck layer.
        stride: default 1, stride of the first layer.
        conv_shortcut: default True, use convolution shortcut if True,
            otherwise identity shortcut.
        name: string, block label.

    # Returns
        Output tensor for the residual block.
    """
    bn_axis = 2 if backend.image_data_format() == 'channels_last' else 1

    if conv_shortcut is True:
        shortcut = layers.Conv1D(4 * filters, 1, strides=stride, kernel_initializer=kernel_initializer,
                                 name=name + '_0_conv')(x)
        shortcut = layers.BatchNormalization(axis=bn_axis, epsilon=1.001e-5,
                                             name=name + '_0_bn')(shortcut)
    else:
        shortcut = x

    x = layers.Conv1D(filters, 1, strides=stride, kernel_initializer=kernel_initializer, name=name + '_1_conv')(x)
    x = layers.BatchNormalization(axis=bn_axis, epsilon=1.001e-5,
                                  name=name + '_1_bn')(x)
    x = layers.Activation('relu', name=name + '_1_relu')(x)

    x = layers.Conv1D(filters, kernel_size, padding='SAME', kernel_initializer=kernel_initializer,
                      name=name + '_2_conv')(x)
    x = layers.BatchNormalization(axis=bn_axis, epsilon=1.001e-5,
                                  name=name + '_2_bn')(x)
    x = layers.Activation('relu', name=name + '_2_relu')(x)

    x = layers.Conv1D(4 * filters, 1, kernel_initializer=kernel_initializer, name=name + '_3_conv')(x)
    x = layers.BatchNormalization(axis=bn_axis, epsilon=1.001e-5,
                                  name=name + '_3_bn')(x)

    x = layers.Add(name=name + '_add')([shortcut, x])
    x = layers.Activation('relu', name=name + '_out')(x)
    return x


def stack1(x, filters, blocks, stride1=2, kernel_initializer='he_uniform', name=None):
    """A set of stacked residual blocks.

    # Arguments
        x: input tensor.
        filters: integer, filters of the bottleneck layer in a block.
        blocks: integer, blocks in the stacked blocks.
        stride1: default 2, stride of the first layer in the first block.
        name: string, stack label.

    # Returns
        Output tensor for the stacked blocks.
    """
    x = block1(x, filters, stride=stride1, kernel_initializer=kernel_initializer, name=name + '_block1')
    for i in range(2, blocks + 1):
        x = block1(x, filters, conv_shortcut=False, kernel_initializer=kernel_initializer, name=name + '_block' + str(i))
    return x


def block2(x, filters, kernel_size=3, stride=1, kernel_initializer="he_uniform",
           conv_shortcut=False, name=None):
    """A residual block.

    # Arguments
        x: input tensor.
        filters: integer, filters of the bottleneck layer.
        kernel_size: default 3, kernel size of the bottleneck layer.
        stride: default 1, stride of the first layer.
        conv_shortcut: default False, use convolution shortcut if True,
            otherwise identity shortcut.
        name: string, block label.

    # Returns
        Output tensor for the residual block.
    """
    bn_axis = 2 if backend.image_data_format() == 'channels_last' else 1

    preact = layers.BatchNormalization(axis=bn_axis, epsilon=1.001e-5,
                                       name=name + '_preact_bn')(x)
    preact = layers.Activation('relu', name=name + '_preact_relu')(preact)

    if conv_shortcut is True:
        shortcut = layers.Conv1D(4 * filters, 1, strides=stride, kernel_initializer=kernel_initializer,
                                 name=name + '_0_conv')(preact)
    else:
        shortcut = layers.MaxPooling1D(1, strides=stride)(x) if stride > 1 else x

    x = layers.Conv1D(filters, 1, strides=1, use_bias=False, kernel_initializer=kernel_initializer,
                      name=name + '_1_conv')(preact)
    x = layers.BatchNormalization(axis=bn_axis, epsilon=1.001e-5,
                                  name=name + '_1_bn')(x)
    x = layers.Activation('relu', name=name + '_1_relu')(x)

    x = layers.ZeroPadding1D(padding=0, name=name + '_2_pad')(x)
    x = layers.Conv1D(filters, kernel_size, strides=stride, kernel_initializer=kernel_initializer,
                      use_bias=False, name=name + '_2_conv')(x)
    x = layers.BatchNormalization(axis=bn_axis, epsilon=1.001e-5,
                                  name=name + '_2_bn')(x)
    x = layers.Activation('relu', name=name + '_2_relu')(x)

    x = layers.Conv1D(4 * filters, 1, kernel_initializer=kernel_initializer, name=name + '_3_conv')(x)
    x = layers.Add(name=name + '_out')([shortcut, x])
    return x


def stack2(x, filters, blocks, stride1=2, kernel_initializer='he_uniform', name=None):
    """A set of stacked residual blocks.

    # Arguments
        x: input tensor.
        filters: integer, filters of the bottleneck layer in a block.
        blocks: integer, blocks in the stacked blocks.
        stride1: default 2, stride of the first layer in the first block.
        name: string, stack label.

    # Returns
        Output tensor for the stacked blocks.
    """
    x = block2(x, filters, conv_shortcut=True, kernel_initializer=kernel_initializer, name=name + '_block1')
    for i in range(2, blocks):
        x = block2(x, filters, name=name + '_block' + str(i))
    x = block2(x, filters, stride=stride1, kernel_initializer=kernel_initializer, name=name + '_block' + str(blocks))
    return x


def ResNet(stack_fn,
           preact,
           use_bias,
           model_name='resnet',
           include_top=True,
           weights=None,
           input_tensor=None,
           input_shape=None,
           pooling=None,
           classes=1000,
            kernel_initializer="he_uniform",
           **kwargs):
    """Instantiates the ResNet, ResNetV2, and ResNeXt architecture.

    Optionally loads weights pre-trained on ImageNet.
    Note that the data format convention used by the model is
    the one specified in your Keras config at `~/.keras/keras.json`.

    # Arguments
        stack_fn: a function that returns output tensor for the
            stacked residual blocks.
        preact: whether to use pre-activation or not
            (True for ResNetV2, False for ResNet and ResNeXt).
        use_bias: whether to use biases for convolutional layers or not
            (True for ResNet and ResNetV2, False for ResNeXt).
        model_name: string, model name.
        include_top: whether to include the fully-connected
            layer at the top of the network.
        weights: one of `None` (random initialization),
              or the path to the weights file to be loaded.
        input_tensor: optional Keras tensor
            (i.e. output of `layers.Input()`)
            to use as image input for the model.
        input_shape: optional shape tuple, only to be specified
            if `include_top` is False (otherwise the input shape
            has to be `(224, 224, 3)` (with `channels_last` data format)
            or `(3, 224, 224)` (with `channels_first` data format).
            It should have exactly 3 inputs channels.
        pooling: optional pooling mode for feature extraction
            when `include_top` is `False`.
            - `None` means that the output of the model will be
                the 4D tensor output of the
                last convolutional layer.
            - `avg` means that global average pooling
                will be applied to the output of the
                last convolutional layer, and thus
                the output of the model will be a 2D tensor.
            - `max` means that global max pooling will
            - `max` means that global max pooling will
                be applied.
        classes: optional number of classes to classify images
            into, only to be specified if `include_top` is True, and
            if no `weights` argument is specified.

    # Returns
        A Keras model instance.

    # Raises
        ValueError: in case of invalid argument for `weights`,
            or invalid input shape.
    """
    global backend, layers, models, utils
    backend, layers, models, utils = get_submodules_from_kwargs(kwargs)

    if not (weights is None or os.path.exists(weights)):
        raise ValueError('The `weights` argument should be either '
                         '`None` (random initialization), '
                         'or the path to the weights file to be loaded.')

    # Determine proper input shape
    input_shape = _obtain_input_shape_1d(input_shape,
                                     min_size=32,
                                     data_format=backend.image_data_format())

    if input_tensor is None:
        img_input = layers.Input(shape=input_shape)
    else:
        if not backend.is_keras_tensor(input_tensor):
            img_input = layers.Input(tensor=input_tensor, shape=input_shape)
        else:
            img_input = input_tensor

    bn_axis = 2 if backend.image_data_format() == 'channels_last' else 1

    x = layers.ZeroPadding1D(padding=3, name='conv1_pad')(img_input)
    x = layers.Conv1D(filters=64, kernel_size=7, strides=2, kernel_initializer=kernel_initializer,
                      use_bias=use_bias, name='conv1_conv')(x)

    if preact is False:
        x = layers.BatchNormalization(axis=bn_axis, epsilon=1.001e-5,
                                      name='conv1_bn')(x)
        x = layers.Activation('relu', name='conv1_relu')(x)

    x = layers.ZeroPadding1D(padding=1, name='pool1_pad')(x)
    x = layers.MaxPooling1D(3, strides=2, name='pool1_pool')(x)

    x = stack_fn(x)

    if preact is True:
        x = layers.BatchNormalization(axis=bn_axis, epsilon=1.001e-5,
                                      name='post_bn')(x)
        x = layers.Activation('relu', name='post_relu')(x)

    if include_top:
        x = layers.GlobalAveragePooling1D(name='avg_pool')(x)
        x = layers.Dense(classes, activation='softmax', name='probs')(x)
    else:
        if pooling == 'avg':
            x = layers.GlobalAveragePooling1D(name='avg_pool')(x)
        elif pooling == 'max':
            x = layers.GlobalMaxPooling1D(name='max_pool')(x)

    # Ensure that the model takes into account
    # any potential predecessors of `input_tensor`.
    if input_tensor is not None:
        inputs = utils.get_source_inputs(input_tensor)
    else:
        inputs = img_input

    # Create model.
    model = models.Model(inputs, x, name=model_name)

    # Load weights.
    if weights is not None:
        model.load_weights(weights)

    return model


def ResNet18(include_top=True,
             weights=None,
             input_tensor=None,
             input_shape=None,
             pooling=None,
             classes=1000,
             kernel_initializer='he_uniform',
             **kwargs):
    def stack_fn(x):
        x = stack0(x, 64, 2, stride1=1, kernel_initializer=kernel_initializer, name='conv2')
        x = stack0(x, 128, 2, kernel_initializer=kernel_initializer, name='conv3')
        x = stack0(x, 256, 2, kernel_initializer=kernel_initializer, name='conv4')
        x = stack0(x, 512, 2, kernel_initializer=kernel_initializer, name='conv5')
        return x
    return ResNet(stack_fn, False, True, 'resnet18',
                  include_top, weights,
                  input_tensor, input_shape,
                  pooling, classes, kernel_initializer,
                  **kwargs)


def ResNet34(include_top=True,
             weights=None,
             input_tensor=None,
             input_shape=None,
             pooling=None,
             classes=1000,
             kernel_initializer='he_uniform',
             **kwargs):
    def stack_fn(x):
        x = stack0(x, 64, 3, stride1=1, kernel_initializer=kernel_initializer, name='conv2')
        x = stack0(x, 128, 4, kernel_initializer=kernel_initializer, name='conv3')
        x = stack0(x, 256, 6, kernel_initializer=kernel_initializer, name='conv4')
        x = stack0(x, 512, 3, kernel_initializer=kernel_initializer, name='conv5')
        return x
    return ResNet(stack_fn, False, True, 'resnet34',
                  include_top, weights,
                  input_tensor, input_shape,
                  pooling, classes, kernel_initializer,
                  **kwargs)


def ResNet50(include_top=True,
             weights=None,
             input_tensor=None,
             input_shape=None,
             pooling=None,
             classes=1000,
             kernel_initializer='he_uniform',
             **kwargs):
    def stack_fn(x):
        x = stack1(x, 64, 3, stride1=1, kernel_initializer=kernel_initializer, name='conv2')
        x = stack1(x, 128, 4, kernel_initializer=kernel_initializer, name='conv3')
        x = stack1(x, 256, 6, kernel_initializer=kernel_initializer, name='conv4')
        x = stack1(x, 512, 3, kernel_initializer=kernel_initializer, name='conv5')
        return x
    return ResNet(stack_fn, False, True, 'resnet50',
                  include_top, weights,
                  input_tensor, input_shape,
                  pooling, classes, kernel_initializer,
                  **kwargs)


def ResNet101(include_top=True,
              weights=None,
              input_tensor=None,
              input_shape=None,
              pooling=None,
              classes=1000,
              kernel_initializer='he_uniform',
              **kwargs):
    def stack_fn(x):
        x = stack1(x, 64, 3, stride1=1, kernel_initializer=kernel_initializer, name='conv2')
        x = stack1(x, 128, 4, kernel_initializer=kernel_initializer, name='conv3')
        x = stack1(x, 256, 23, kernel_initializer=kernel_initializer, name='conv4')
        x = stack1(x, 512, 3, kernel_initializer=kernel_initializer, name='conv5')
        return x
    return ResNet(stack_fn, False, True, 'resnet101',
                  include_top, weights,
                  input_tensor, input_shape,
                  pooling, classes, kernel_initializer,
                  **kwargs)


def ResNet152(include_top=True,
              weights=None,
              input_tensor=None,
              input_shape=None,
              pooling=None,
              classes=1000,
              kernel_initializer='he_uniform',
              **kwargs):
    def stack_fn(x):
        x = stack1(x, 64, 3, stride1=1, kernel_initializer=kernel_initializer, name='conv2')
        x = stack1(x, 128, 8, kernel_initializer=kernel_initializer, name='conv3')
        x = stack1(x, 256, 36, kernel_initializer=kernel_initializer, name='conv4')
        x = stack1(x, 512, 3, kernel_initializer=kernel_initializer, name='conv5')
        return x
    return ResNet(stack_fn, False, True, 'resnet152',
                  include_top, weights,
                  input_tensor, input_shape,
                  pooling, classes, kernel_initializer,
                  **kwargs)


def ResNet50V2(include_top=True,
               weights=None,
               input_tensor=None,
               input_shape=None,
               pooling=None,
               classes=1000,
               kernel_initializer='he_uniform',
               **kwargs):
    def stack_fn(x):
        x = stack2(x, 64, 3, kernel_initializer=kernel_initializer, name='conv2')
        x = stack2(x, 128, 4, kernel_initializer=kernel_initializer, name='conv3')
        x = stack2(x, 256, 6, kernel_initializer=kernel_initializer, name='conv4')
        x = stack2(x, 512, 3, stride1=1, kernel_initializer=kernel_initializer, name='conv5')
        return x
    return ResNet(stack_fn, True, True, 'resnet50v2',
                  include_top, weights,
                  input_tensor, input_shape,
                  pooling, classes, kernel_initializer,
                  **kwargs)


def ResNet101V2(include_top=True,
                weights=None,
                input_tensor=None,
                input_shape=None,
                pooling=None,
                classes=1000,
                kernel_initializer='he_uniform',
                **kwargs):
    def stack_fn(x):
        x = stack2(x, 64, 3, kernel_initializer=kernel_initializer, name='conv2')
        x = stack2(x, 128, 4, kernel_initializer=kernel_initializer, name='conv3')
        x = stack2(x, 256, 23, kernel_initializer=kernel_initializer, name='conv4')
        x = stack2(x, 512, 3, stride1=1, kernel_initializer=kernel_initializer, name='conv5')
        return x
    return ResNet(stack_fn, True, True, 'resnet101v2',
                  include_top, weights,
                  input_tensor, input_shape,
                  pooling, classes, kernel_initializer,
                  **kwargs)


def ResNet152V2(include_top=True,
                weights=None,
                input_tensor=None,
                input_shape=None,
                pooling=None,
                classes=1000,
                kernel_initializer='he_uniform',
                **kwargs):
    def stack_fn(x):
        x = stack2(x, 64, 3, kernel_initializer=kernel_initializer, name='conv2')
        x = stack2(x, 128, 8, kernel_initializer=kernel_initializer, name='conv3')
        x = stack2(x, 256, 36, kernel_initializer=kernel_initializer, name='conv4')
        x = stack2(x, 512, 3, stride1=1, kernel_initializer=kernel_initializer, name='conv5')
        return x
    return ResNet(stack_fn, True, True, 'resnet152v2',
                  include_top, weights,
                  input_tensor, input_shape,
                  pooling, classes, kernel_initializer,
                  **kwargs)


setattr(ResNet18, '__doc__', ResNet.__doc__)
setattr(ResNet34, '__doc__', ResNet.__doc__)
setattr(ResNet50, '__doc__', ResNet.__doc__)
setattr(ResNet101, '__doc__', ResNet.__doc__)
setattr(ResNet152, '__doc__', ResNet.__doc__)
setattr(ResNet50V2, '__doc__', ResNet.__doc__)
setattr(ResNet101V2, '__doc__', ResNet.__doc__)
setattr(ResNet152V2, '__doc__', ResNet.__doc__)
