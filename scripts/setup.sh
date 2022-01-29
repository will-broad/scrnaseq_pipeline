#!/bin/bash

"""
UGER LOCAL RUN SETUP
"""
use UGER
ish -l h_vmem=3g -l os=RedHat7 -pe smp 12 -R y -binding linear:12
reuse Anaconda3
conda create --prefix /broad/xavierlab_datadeposit/dchafamo/scrnaseq-pipeline python=3 pip
conda activate /broad/xavierlab_datadeposit/dchafamo/scrnaseq-pipeline
conda install pandas
pip install firecloud
pip install altocumulus


"""
SERVICE ACCOUNT CREATION AND TERRA SETUP
"""
gcloud config set project "microbiome-xavier"
gcloud iam service-accounts create "scrnaseq-pipeline" \
    --description="Service account to run KCO scrnaseq-pipeline" \
    --display-name="scrnaseq-pipeline-sa"
gcloud iam service-accounts keys create "$HOME/local/configs/scrnaseq-pipeline-sa.json" \
    --iam-account="scrnaseq-pipeline@microbiome-xavier.iam.gserviceaccount.com"
git clone https://github.com/broadinstitute/terra-tools.git && cd terra-tools || exit
python3 scripts/register_service_account/register_service_account.py -j "$HOME/local/configs/scrnaseq-pipeline-sa.json" -e "dchafamo@broadinstitute.org"
cd ../ && rm -rf terra-tools
# The service account scrnaseq-pipeline@microbiome-xavier.iam.gserviceaccount.com is now registered with Terra. You can share workspaces with this address, or use it to call APIs.
# add to terra Group + share workspace with service account


"""
GOOGLE CLOUD VM SETUP
"""
cd /tmp || exit
sudo apt install unzip
curl -O https://repo.anaconda.com/archive/Anaconda3-2021.05-Linux-x86_64.sh
bash Anaconda3-2021.05-Linux-x86_64.sh
conda init
# restart shell
conda create --name scrnaseq-pipeline -y python=3 pip
conda activate scrnaseq-pipeline
conda install pandas -y
conda install -c conda-forge google-cloud-sdk oauth2client -y
pip install altocumulus firecloud tabulate
# copy service account key to /tmp/service_account.json
export GOOGLE_APPLICATION_CREDENTIALS='/tmp/service_account.json'
nohup python sc_pipeline.py &> sc_out.txt &


"""
DSUB WITH CUSTOM DOCKER IMAGE AND SERVICE ACCOUNT
"""
cd docker || exit
docker build -t conda-alto-0.0.1 .
docker tag conda-alto-0.0.1 gcr.io/microbiome-xavier/conda-alto:0.0.1
docker push gcr.io/microbiome-xavier/conda-alto:0.0.1
gsutil iam ch serviceAccount:scrnaseq-pipeline@microbiome-xavier.iam.gserviceaccount.com:objectViewer gs://us.artifacts.microbiome-xavier.appspot.com/
gsutil iam ch serviceAccount:scrnaseq-pipeline@microbiome-xavier.iam.gserviceaccount.com:objectViewer gs://artifacts.microbiome-xavier.appspot.com/

gcloud auth configure-docker

dsub --provider google-cls-v2 --project "microbiome-xavier" --regions us-east1 \
  --service-account "scrnaseq-pipeline@microbiome-xavier.iam.gserviceaccount.com" \
  --image "gcr.io/microbiome-xavier/conda-alto" \
  --logging "gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/scrnaseq-pipeline-logs/" \
  --script submit.sh


"""
GCP GCE VM R ENV
"""
sudo apt install r-base-core libssl-dev libcurl4-openssl-dev


"""
UGER R ENV SETUP
"""
conda create --prefix /broad/xavierlab_datadeposit/dchafamo/rEnvNew python=3 pip
conda activate /broad/xavierlab_datadeposit/dchafamo/rEnvNew
conda install -c conda-forge boost gcc libgcc llvm libboost openmpi
use R-3.5
export LIBRARY_PATH=${CONDA_PREFIX}/lib:$LIBRARY_PATH
export LD_LIBRARY_PATH=${CONDA_PREFIX}/lib:$LD_LIBRARY_PATH
R
# library(devtools)
# .libPaths( c( "~/rLibs" , .libPaths() ) )
# install_github("velocyto-team/velocyto.R")