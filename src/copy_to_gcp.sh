use UGER
ish -l h_vmem=3g -l os=RedHat7 -pe smp 12 -R y -binding linear:12

source /broad/software/scripts/useuse
use Google-Cloud-SDK
gcloud auth login dchafamo@broadinstitute.org
gsutil -m cp -r /ahg/regev_nextseq/Data02/211015_NB501337_0916_AH7MMWBGXK gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/gut_eqtl/bcl_GIDER/211015_NB501337_0916_AH7MMWBGXK