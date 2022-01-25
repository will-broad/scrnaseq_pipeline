from utils import *
import pandas as pd
import concurrent.futures
import steps
import threading

project_name = "gut_eqtl8"
sample_tracking_file = os.getcwd() + "/sampletracking_guteqtl_rerun.csv"
gcp_basedir = "gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/gut_eqtl8"
email = "dchafamo@broadinstitute.org"
alto_workspace = "'kco-tech/Gut_eQTL'"
cellranger_version = "6.0.1"
max_parallel_threads = 30

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
alto_dirs = build_alto_folders(buckets)


def process_sample(seq_dir):
    logging.info("Started processing samples in {}".format(seq_dir))
    sample_tracking = sample_tracking_alldata[sample_tracking_alldata.run_pipeline &
                                              (sample_tracking_alldata.seq_dir == seq_dir)]

    threading.current_thread().name = 'Thread:' + sample_tracking['flowcell'].iloc[0]
    sample_tracking['Sample'] = sample_tracking['sampleid']
    sample_tracking = sample_tracking[
        ['date', 'run_pipeline', 'Channel Name', 'Sample', 'sampleid', 'condition', 'replicate', 'tissue', 'Lane',
         'Index', 'project', 'reference', 'introns', 'chemistry', 'flowcell', 'seq_dir', 'min_umis', 'min_genes',
         'percent_mito', 'cellbender_expected_cells', 'cellbender_total_droplets_included']]
    logging.info(sample_tracking)

    sample_dicts = build_sample_dicts(sample_tracking, sample_tracking['sampleid'].tolist())

    steps.upload_cellranger_mkfastq_input(buckets, directories, sample_tracking, cellranger_version)
    steps.run_cellranger_mkfastq(directories, sample_tracking, alto_workspace, alto_dirs['alto_fastqs'])

    steps.upload_cellranger_count_input(buckets, directories, sample_dicts, sample_tracking, cellranger_version)
    steps.run_cellranger_count(directories, sample_dicts, sample_tracking, alto_workspace, alto_dirs['alto_counts'])

    steps.upload_cumulus_samplesheet(buckets, directories, sample_dicts, sample_tracking, count_matrix_name)
    steps.run_cumulus(directories, sample_dicts, sample_tracking, alto_workspace, alto_dirs['alto_results'])

    steps.upload_cell_bender_input(buckets, directories, sample_dicts, sample_tracking, count_matrix_name)
    steps.run_cellbender(directories, sample_dicts, sample_tracking, alto_workspace, alto_dirs['alto_cellbender'])

    steps.upload_post_cellbender_cumulus_input(buckets, directories, sample_dicts, sample_tracking, cellbender_matrix_name)
    steps.run_cumulus_post_cellbender(directories, sample_dicts, sample_tracking, alto_workspace, alto_dirs['alto_results'])


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)-7s | %(threadName)-15s | %(levelname)-5s | %(message)s",
                        level=logging.INFO, datefmt="%m-%d %H:%M", filename='{}/{}.log'.format(basedir,project_name),
                        filemode='w')
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel_threads) as executor:
        executor.map(process_sample, seq_dirs)
