#!/bin/bash

#
# Broad UGER


use UGER
ish -l h_vmem=3g -l os=RedHat7 -pe smp 12 -R y -binding linear:12
reuse Anaconda3
conda create --prefix /broad/xavierlab_datadeposit/dchafamo/alto python=3 pip
conda activate /broad/xavierlab_datadeposit/dchafamo/alto
conda install pandas
pip install firecloud
pip install altocumulus

#
# google cloud VM create

cd /tmp || exit
sudo apt install unzip
curl -O https://repo.anaconda.com/archive/Anaconda3-2021.05-Linux-x86_64.sh
bash Anaconda3-2021.05-Linux-x86_64.sh
conda init
# restart shell
conda create --name alto -y python=3 pip
conda activate alto
conda install pandas -y
conda install -c conda-forge google-cloud-sdk -y
pip install altocumulus
pip install firecloud
pip install tabulate

#
#
conda activate alto
gcloud auth application-default login  --no-launch-browser
nohup python sc_pipeline.py &> sc_out.txt &


#
# R env
sudo apt install r-base-core libssl-dev libcurl4-openssl-dev
