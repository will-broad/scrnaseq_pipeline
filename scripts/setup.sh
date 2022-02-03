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
gcloud auth activate-service-account scrnaseq-pipeline@microbiome-xavier.iam.gserviceaccount.com --key-file=/home/dchafamo/.config/gcloud/sa.json --project=microbiome-xavier
nohup python sc_pipeline.py &> sc_out.txt &


"""
DSUB WITH CUSTOM DOCKER IMAGE AND SERVICE ACCOUNT
"""
cd docker || exit
docker build -t conda-alto-0.0.1 .
docker tag conda-alto-0.0.1 gcr.io/microbiome-xavier/conda-alto:0.0.1
docker push gcr.io/microbiome-xavier/conda-alto:0.0.1

gsutil iam ch serviceAccount:scrnaseq-pipeline@microbiome-xavier.iam.gserviceaccount.com:objectViewer gs://artifacts.microbiome-xavier.appspot.com/
gsutil iam ch group:klarman_cell_observatory@firecloud.org:objectViewer gs://artifacts.microbiome-xavier.appspot.com/


gcloud auth configure-docker

dsub --provider google-cls-v2 --project "microbiome-xavier" --regions us-east1 \
  --service-account "scrnaseq-pipeline@microbiome-xavier.iam.gserviceaccount.com" \
  --image "gcr.io/microbiome-xavier/conda-alto" --disk-size '10' --timeout '2d'\
  --logging "gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/scp-test/logs/" \
  --command "wget http://github.com/dan-broad/scrnaseq_pipeline/archive/master.zip && unzip master.zip && cd scrnaseq_pipeline-master/src && python sc_pipeline.py" \
  --output PIPELINE_LOGS="gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/scp-test/logs/execution.log" \
  --input SAMPLE_TRACKING_FILE="gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/scp-test/sample_tracking_small.csv" \
  --env PROJECT_NAME="scp-test" \
  --env GCP_BUCKET_BASEDIR="gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/scp-test" \
  --env EMAIL="dchafamo@broadinstitute.org" \
  --env TERRA_WORKSPACE="'kco-tech/Gut_eQTL'" \

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

"""
R VM INSTALL
"""
wget -qO- https://cloud.r-project.org/bin/linux/ubuntu/marutter_pubkey.asc | sudo tee -a /etc/apt/trusted.gpg.d/cran_ubuntu_key.asc
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install r-base r-base-dev
sudo apt-get install gdebi-core
wget https://download2.rstudio.org/server/bionic/amd64/rstudio-server-1.2.5019-amd64.deb
sudo gdebi rstudio-server-1.2.5019-amd64.deb
sudo apt-get install libcurl4-openssl-dev libssl-dev libxml2-dev
sudo adduser rstudio
sudo rstudio-server start
sudo usermod -aG sudo rstudio
sudo usermod -aG dchafamo rstudio


"""
"""
conda install -c r r=4.0.1 rstudio
conda install -c conda-forge r-rcurl r-reticulate r-ggplot2 r-ggplot2 r-tidyverse r-seurat r-gridExtra r-grid r-pheatmap r-gsa
conda install -c bioconda bioconductor-singler bioconductor-celldex
alias rstudio3umap="RSTUDIO_WHICH_R=/Users/shu/anaconda3/envs/r_3.5.1/bin/R open -a rstudio"
/Users/dchafamo/local/projects/scrnaseq_pipeline/analysis/umap3/lib/R/bin/R
# .libPaths(c("/Users/dchafamo/local/projects/scrnaseq_pipeline/analysis/umap3/lib/R/library", .libPaths())

