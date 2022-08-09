#!/bin/bash

#
# conda create -n dsub_env python=3 pip
# conda activate dsub_env
# pip install --upgrade dsub
# conda install -c conda-forge google-cloud-sdk
# gcloud auth configure-docker
#

# conda activate dsub_env

dir_name="finngen_multiome"
gcp_bucket_basedir="gs://fc-secure-d4adbbf9-8265-4a5c-b14f-23a5f1b5c4f9/${dir_name}"
sample_tracking_file="${gcp_bucket_basedir}/sampletracking_multiome.csv"
project_name="finngen_multiome"
email="dchafamo@broadinstitute.org"
workspace="'693-finland-v2f/Finngen'"
count_matrix_name="raw_feature_bc_matrix.h5"
steps="MKFASTQ,COUNT,CUMULUS"
cellranger_method="broadinstitute:cumulus:Cellranger:master"

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
  --env CELLRANGER_METHOD="$cellranger_method"