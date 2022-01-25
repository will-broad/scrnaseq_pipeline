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
# google cloud VM

cd /tmp || exit
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

gcloud auth application-default login  --no-launch-browser

