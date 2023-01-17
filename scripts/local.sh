#!/bin/bash

#
# conda create -n dsub_env python=3 pip
# conda activate dsub_env
# pip install --upgrade dsub
# conda install -c conda-forge google-cloud-sdk
# gcloud auth configure-docker
#

# conda activate dsub_env

dir_name="tutorial"
gcp_bucket_basedir="gs://fc-secure-15bf93cd-d43c-4a70-b7de-0ee36bf3a52a/${dir_name}"
sample_tracking_file="${gcp_bucket_basedir}/sampletracking_small.csv"
project_name="tutorial"
email="dchafamo@broadinstitute.org"
workspace="'kco-tech/sc_pipeline_tutorial'"
count_matrix_name="raw_feature_bc_matrix.h5"
steps="MKFASTQ,COUNT,CUMULUS,CELLBENDER,CELLBENDER_CUMULUS"
mkfastq_memory="120G"
mkfastq_diskspace="1500"
cellranger_method="broadinstitute:cumulus:Cellranger:2.1.1"
cumulus_method="broadinstitute:cumulus:cumulus:2.1.1"
cellbender_method="broadinstitute:cumulus:CellBender:2.3.0"
cellranger_version="7.0.1"
cellranger_atac_version="2.1.0"
cellranger_arc_version="2.0.1"


dsub --provider google-cls-v2 --project "microbiome-xavier" --regions us-east1 \
  --service-account "scrnaseq-pipeline@microbiome-xavier.iam.gserviceaccount.com" \
  --image "gcr.io/microbiome-xavier/conda-alto" --disk-size '10' --timeout '2d'\
  --logging "$gcp_bucket_basedir/logs/" \
  --command "wget http://github.com/dan-broad/scrnaseq_pipeline/archive/master.zip && unzip master.zip && cd scrnaseq_pipeline-master/src && python sc_pipeline.py" \
  --output PIPELINE_LOGS="$gcp_bucket_basedir/logs/execution.log" \
  --input SAMPLE_TRACKING_FILE="$sample_tracking_file" \
  --env PROJECT_NAME="$project_name" \
  --env GCP_BUCKET_BASEDIR="$gcp_bucket_basedir" \
  --env EMAIL="$email" \
  --env TERRA_WORKSPACE="$workspace" \
  --env COUNT_MATRIX_NAME="$count_matrix_name" \
  --env STEPS="$steps" \
  --env CELLRANGER_METHOD="$cellranger_method" \
  --env CUMULUS_METHOD="$cumulus_method" \
  --env CELLBENDER_METHOD="$cellbender_method" \
  --env CELLRANGER_VERSION="$cellranger_version" \
  --env CELLRANGER_ATAC_VERSION="$cellranger_atac_version" \
  --env CELLRANGER_ARC_VERSION="$cellranger_arc_version" \
  --env MKFASTQ_DISKSPACE="$mkfastq_diskspace" \
  --env MKFASTQ_MEMORY="$mkfastq_memory"