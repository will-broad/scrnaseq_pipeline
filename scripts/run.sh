#!/usr/bin/env bash

# Usage:
#  bash run.sh --project-name "scp-test" \
#   --gcp-bucket-basedir "gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/scp-test" \
#   --sample-tracking-file "gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/scp-test/sample_tracking_small.csv" \
#   --email "dchafamo@broadinstitute.org" \
#   --workspace "'kco-tech/Gut_eQTL'" \
#   --count-matrix-name "raw_feature_bc_matrix.h5"

while [ $# -gt 0 ]; do
  case "$1" in
    --project-name)
      project_name="$2"
      ;;
    --gcp-bucket-basedir)
      gcp_bucket_basedir="$2"
      ;;
    --sample-tracking-file)
      sample_tracking_file="$2"
      ;;
    --email)
      email="$2"
      ;;
    --workspace)
      workspace="$2"
      ;;
    --count-matrix-name)
      count_matrix_name="$2"
      ;;
    *)
      printf "***************************\n"
      printf "* Error: Invalid argument.*\n"
      printf "***************************\n"
      exit 1
  esac
  shift
  shift
done

pip install --upgrade dsub
gcloud auth configure-docker

dsub --provider google-cls-v2 --project "microbiome-xavier" --regions us-east1 \
  --service-account "scrnaseq-pipeline@microbiome-xavier.iam.gserviceaccount.com" \
  --image "gcr.io/microbiome-xavier/conda-alto" --disk-size '10' --timeout '2d'\
  --logging "gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/Gut_eQTL_0202/logs/" \
  --command "wget http://github.com/dan-broad/scrnaseq_pipeline/zipball/master -O master.zip && unzip master.zip && cd dan-broad-scrnaseq_pipeline-b2e078a/src && python sc_pipeline.py" \
  --output PIPELINE_LOGS="gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/Gut_eQTL_0202/logs/execution_02022022.log" \
  --input SAMPLE_TRACKING_FILE="gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/Gut_eQTL_0202/sampletracking_guteqtl_0202222.csv" \
  --env PROJECT_NAME="Gut_eQTL_0202" \
  --env GCP_BUCKET_BASEDIR="gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/Gut_eQTL_0202" \
  --env EMAIL="dchafamo@broadinstitute.org" \
  --env TERRA_WORKSPACE="'kco-tech/Gut_eQTL'" \
  --env COUNT_MATRIX_NAME="filtered_feature_bc_matrix.h5"