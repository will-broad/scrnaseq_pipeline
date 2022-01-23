#!/usr/bin/env python
# coding: utf-8

from utils import *
import pandas as pd

project_name = "gut_eqtl"
sample_tracking_file = os.getcwd() + "/sampletracking_guteqtl_rerun.csv"
gcp_basedir = "gs://fc-secure-1620151c-e00c-456d-9daf-4d222e1cab18/gut_eqtl"
email = "dchafamo@broadinstitute.org"
alto_workspace = "'kco-tech/Gut_eQTL'"
cellranger_version = "6.0.1"


cwd = os.getcwd()
basedir = cwd + "/" + project_name + "/sc_processed"
os.makedirs(basedir, exist_ok=True)

directories = build_directories(basedir)

sample_tracking_alldata = pd.read_csv(sample_tracking_file)
sample_tracking = sample_tracking_alldata[sample_tracking_alldata.run_pipeline == True]

project = sample_tracking['project'].tolist()[0]
seq_dirs = set(sample_tracking['seq_dir'])

buckets = build_buckets(gcp_basedir, project)
alto_folders = build_alto_folders(buckets)

for run_alto_file in ["%s/run_alto_cellranger_workflow.sh" % (directories['counts']),
                      "%s/run_alto_cumulus.sh" % (directories['results']),
                      "%s/run_alto_cellbender.sh" % (directories['cellbender']),
                      "%s/run_alto_cellbender_cumulus.sh" % (directories['cellbender_results'])]:
    open(run_alto_file, "w").close()

count_matrix_name = "raw_feature_bc_matrix.h5"
filtered_matrix_name = "filtered_feature_bc_matrix.h5"
cellbender_matrix_name = "out_FPR_0.01_filtered.h5"

for seq_dir in seq_dirs:

    sample_tracking = sample_tracking_alldata[(sample_tracking_alldata.run_pipeline == True) &
                                              (sample_tracking_alldata.seq_dir == seq_dir)]

    flowcellid = sample_tracking['flowcell'].tolist()[0]
    date = sample_tracking['date'].tolist()[0]

    sample_tracking['Sample'] = sample_tracking['sampleid']
    sample_tracking = sample_tracking[
        ['date', 'run_pipeline', 'Channel Name', 'Sample', 'sampleid', 'condition', 'replicate', 'tissue', 'Lane',
         'Index', 'project', 'reference', 'introns', 'chemistry', 'flowcell', 'seq_dir', 'min_umis', 'min_genes',
         'percent_mito', 'cellbender_expected_cells', 'cellbender_total_droplets_included']]
    print(sample_tracking)

    sampleids = sample_tracking['sampleid'].tolist()

    sample_dicts = build_sample_dicts(sample_tracking, sampleids)

    upload_cell_ranger_samplesheet_and_input(buckets, directories, sample_dicts, cellranger_version)
    run_cell_ranger_mkfastq_and_count(directories, sample_dicts, alto_workspace, alto_folders['alto_counts'])
    upload_cumulus_samplesheet(buckets, directories, sample_dicts, sample_tracking, count_matrix_name)
    run_cumulus(directories, sample_dicts, alto_workspace, alto_folders['alto_results'])
    upload_cell_bender_input(buckets, directories, sample_dicts, sample_tracking, count_matrix_name)
    run_cellbender(directories, sample_dicts, alto_workspace, alto_folders['alto_cellbender'])
    upload_post_cellbender_cumulus_input(buckets, directories, sample_dicts,sample_tracking, cellbender_matrix_name)
    run_cumulus_post_cellbender(directories, sample_dicts, alto_workspace, alto_folders['alto_results'])

