#!/bin/bash

# Usage:
#  bash run.sh --project-name "scp-test" \
#   --gcp-bucket-basedir "gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/scp-test" \
#   --sample-tracking-file "gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/scp-test/sample_tracking_small.csv" \
#   --email "dchafamo@broadinstitute.org" \
#   --workspace "'kco-tech/Gut_eQTL'"

while [ $# -gt 0 ]; do
  case "$1" in
    --project-name=*)
      project_name="${1#*=}"
      ;;
    --gcp-bucket-basedir=*)
      gcp_bucket_basedir="${1#*=}"
      ;;
    --sample-tracking-file=*)
      sample_tracking_file="${1#*=}"
      ;;
    --email=*)
      email="${1#*=}"
      ;;
    --workspace=*)
      workspace="${1#*=}"
      ;;
    *)
      printf "***************************\n"
      printf "* Error: Invalid argument.*\n"
      printf "***************************\n"
      exit 1
  esac
  shift
done

pip install --upgrade dsub

gcloud auth configure-docker

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
  --env TERRA_WORKSPACE="$workspace"