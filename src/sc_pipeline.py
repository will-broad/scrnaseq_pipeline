import datetime

from utils import *
import pandas as pd
import concurrent.futures
import steps
import threading

project_name = "gut_eqtl12"
sample_tracking_file = os.getcwd() + "/sampletracking_guteqtl_rerun.csv"
gcp_basedir = "gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/gut_eqtl12"
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
master_tracking = pd.read_csv(sample_tracking_file)
project = master_tracking[master_tracking.run_pipeline]['project'].tolist()[0]
master_tracking['seq_dir'] = master_tracking['seq_dir'].apply(lambda sd: sd[:-1] if sd.endswith('/') else sd)
seq_dirs = set(master_tracking[master_tracking.run_pipeline]['seq_dir'])
buckets = build_buckets(gcp_basedir, project)
alto_dirs = build_alto_folders(buckets)


def process_sample(seq_dir):
    sample_tracking = master_tracking[master_tracking.run_pipeline &
                                      (master_tracking.seq_dir == seq_dir)]

    threading.current_thread().name = 'Thread:' + sample_tracking['flowcell'].iloc[0]
    logging.info("Started processing samples in {}".format(seq_dir))

    sample_tracking['Sample'] = sample_tracking['sampleid']
    sample_tracking = sample_tracking[
        ['date', 'run_pipeline', 'Channel Name', 'Sample', 'sampleid', 'condition', 'replicate', 'tissue', 'Lane',
         'Index', 'project', 'reference', 'introns', 'chemistry', 'flowcell', 'seq_dir', 'min_umis', 'min_genes',
         'percent_mito', 'cellbender_expected_cells', 'cellbender_total_droplets_included']]

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
                        level=logging.INFO, datefmt="%m-%d %H:%M", filename='{}/{}.log'.format(basedir, project_name),
                        filemode='w')

    start_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    logging.info("Running scRNASeq pipeline for project {} on {}".format(project, start_time))
    logging.info("GCP User: {}".format(email))
    logging.info("GCP bucket dir: {}".format(gcp_basedir))
    logging.info("Workspace: {}".format(alto_workspace))
    logging.info("Master sample tracking file: \n\n {} \n".format(master_tracking.to_markdown()))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel_threads) as executor:
        executor.map(process_sample, seq_dirs)
