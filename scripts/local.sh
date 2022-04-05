#!/bin/bash

conda activate alto

dir_name="Gut_eQTL_0331_fresh"
gcp_bucket_basedir="gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/${dir_name}"
sample_tracking_file="${gcp_bucket_basedir}/sampletracking_guteqtl_033122_freshgut.csv"
project_name="Gut_eQTL"
email="dchafamo@broadinstitute.org"
workspace="'kco-tech/Gut_eQTL'"
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