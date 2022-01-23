import logging
from utils import *
import pandas as pd
import concurrent.futures

project_name = "gut_eqtl"
sample_tracking_file = os.getcwd() + "/sampletracking_guteqtl_rerun.csv"
gcp_basedir = "gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/gut_eqtl"
email = "dchafamo@broadinstitute.org"
alto_workspace = "'kco-tech/Gut_eQTL'"
cellranger_version = "6.0.1"

count_matrix_name = "raw_feature_bc_matrix.h5"
filtered_matrix_name = "filtered_feature_bc_matrix.h5"
cellbender_matrix_name = "out_FPR_0.01_filtered.h5"

cwd = os.getcwd()
basedir = cwd + "/" + project_name + "/sc_processed"
os.makedirs(basedir, exist_ok=True)
directories = build_directories(basedir)
sample_tracking_alldata = pd.read_csv(sample_tracking_file)
project = sample_tracking_alldata[sample_tracking_alldata.run_pipeline]['project'].tolist()[0]
seq_dirs = set(sample_tracking_alldata[sample_tracking_alldata.run_pipeline]['seq_dir'])
buckets = build_buckets(gcp_basedir, project)
alto_folders = build_alto_folders(buckets)

def process_sample(seq_dir):
    sample_tracking = sample_tracking_alldata[sample_tracking_alldata.run_pipeline &
                                              (sample_tracking_alldata.seq_dir == seq_dir)]

    sample_tracking['Sample'] = sample_tracking['sampleid']
    sample_tracking = sample_tracking[
        ['date', 'run_pipeline', 'Channel Name', 'Sample', 'sampleid', 'condition', 'replicate', 'tissue', 'Lane',
         'Index', 'project', 'reference', 'introns', 'chemistry', 'flowcell', 'seq_dir', 'min_umis', 'min_genes',
         'percent_mito', 'cellbender_expected_cells', 'cellbender_total_droplets_included']]
    print(sample_tracking)

    sample_dicts = build_sample_dicts(sample_tracking, sample_tracking['sampleid'].tolist())

    upload_cell_ranger_samplesheet_and_input(buckets, directories, sample_dicts, cellranger_version)
    run_cell_ranger_mkfastq_and_count(directories, sample_dicts, alto_workspace, alto_folders['alto_counts'])
    upload_cumulus_samplesheet(buckets, directories, sample_dicts, sample_tracking, count_matrix_name)
    run_cumulus(directories, sample_dicts, alto_workspace, alto_folders['alto_results'])
    upload_cell_bender_input(buckets, directories, sample_dicts, sample_tracking, count_matrix_name)
    run_cellbender(directories, sample_dicts, alto_workspace, alto_folders['alto_cellbender'])
    upload_post_cellbender_cumulus_input(buckets, directories, sample_dicts, sample_tracking, cellbender_matrix_name)
    run_cumulus_post_cellbender(directories, sample_dicts, alto_workspace, alto_folders['alto_results'])


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.INFO, datefmt="%H:%M:%S")
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        executor.map(process_sample, seq_dirs)