#!/bin/bash

mkdir -p miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda3/miniconda.sh
bash miniconda3/miniconda.sh -b -u -p miniconda3
conda init bash
conda create --prefix miniconda3/ScPipelineKCO python=3
conda activate ScPipelineKCO -y
pip install altocumulus
pip install pandas
