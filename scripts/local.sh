#!/bin/bash

#
# conda create -n dsub_env python=3 pip
# conda activate dsub_env
# pip install --upgrade dsub
# conda install -c conda-forge google-cloud-sdk
# gcloud auth configure-docker
#

# conda activate dsub_env

dir_name="multiome_automated_test_run"
gcp_bucket_basedir="gs://fc-2cbea049-0464-48ee-9438-1fe5e008747d/${dir_name}"
sample_tracking_file="${gcp_bucket_basedir}/sampletracking_multiome.csv"
project_name="multiome_automated"
email="dchafamo@broadinstitute.org"
workspace="'klarman-6/SHARE-seq_Multiome'"
count_matrix_name="raw_feature_bc_matrix.h5"
steps="MKFASTQ,COUNT,CUMULUS"

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
  --env STEPS="$steps"