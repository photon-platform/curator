Analog Bits: Generating Discrete Data using Diffusion Models with Self-Conditioning
===================================================================================

:Author: Ting Chen, Ruixiang Zhang, Geoffrey Hinton
:Published: 2022-08-08
:URL: https://arxiv.org/abs/2208.04202
:Categories: cs.CV, cs.AI, cs.CL, cs.LG
:PDF: ./2208.04202.pdf

Abstract
--------
We present Bit Diffusion: a simple and generic approach for generating
discrete data with continuous state and continuous time diffusion models. The
main idea behind our approach is to first represent the discrete data as binary
bits, and then train a continuous diffusion model to model these bits as real
numbers which we call analog bits. To generate samples, the model first
generates the analog bits, which are then thresholded to obtain the bits that
represent the discrete variables. We further propose two simple techniques,
namely Self-Conditioning and Asymmetric Time Intervals, which lead to a
significant improvement in sample quality. Despite its simplicity, the proposed
approach can achieve strong performance in both discrete image generation and
image captioning tasks. For discrete image generation, we significantly improve
previous state-of-the-art on both CIFAR-10 (which has 3K discrete 8-bit tokens)
and ImageNet-64x64 (which has 12K discrete 8-bit tokens), outperforming the
best autoregressive model in both sample quality (measured by FID) and
efficiency. For image captioning on MS-COCO dataset, our approach achieves
competitive results compared to autoregressive models.

Keywords
--------
.. todo:: Extract or manually add keywords

Notes
-----
.. todo:: Add reading notes and key insights