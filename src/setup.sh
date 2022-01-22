#!/bin/bash

mkdir -p notebooks/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O notebooks/miniconda3/miniconda.sh
bash notebooks/miniconda3/miniconda.sh -b -u -p miniconda3
conda init bash
conda create ScPipelineKCO -y
pip install altocumulus

