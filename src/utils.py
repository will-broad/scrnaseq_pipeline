import logging
import os
import re
import time
import sys
import firecloud.api as fapi
import subprocess

TERRA_POLL_SPACER = 600
TERRA_TIMEOUT = 18000


def build_directories(basedir):
    directories = {
        'scripts': basedir + "/scripts",
        'logs': basedir + "/logs",
        'fastq': basedir + "/fastq",
        'counts': basedir + "/counts",
        'results': basedir + "/cumulus",
        'cellbender': basedir + "/cellbenderV2",
        'cellbender_results': basedir + "/cellbenderV2_cumulus"
    }
    for directory in directories.values():
        if not os.path.exists(directory):
            os.makedirs(directory)
    return directories


def build_buckets(gcp_basedir, project):
    return {
        'bcl': gcp_basedir + "/bcl_" + project,
        'counts': gcp_basedir + "/counts_" + project,
        'results': gcp_basedir + "/cumulus_" + project,
        'cellbender': gcp_basedir + "/cellbenderv2_" + project,
        'cellbender_results': gcp_basedir + "/cellbenderv2_cumulus_" + project
    }


def build_alto_folders(buckets):
    return {
        'alto_counts': re.sub(r'^gs://.*/', "", buckets['counts']),
        'alto_results': re.sub(r'^gs://.*/', "", buckets['results']),
        'alto_cellbender': re.sub(r'^gs://.*/', "", buckets['cellbender']),
        'alto_cellbender_results': re.sub(r'^gs://.*/', "", buckets['cellbender_results'])
    }


def build_sample_dicts(sample_tracking, sampleids):
    sample_dict = dict([(sample, []) for sample in sampleids])
    mkfastq_dict = dict()
    cumulus_dict = dict()
    cellbender_dict = dict()
    cellranger_dict = dict()
    for index, row in sample_tracking.iterrows():
        sample_dict[row['sampleid']].append(row['Sample'])
        mkfastq_dict[row['Sample']] = [row['Lane'], row['Index'], row['reference'], row['chemistry']]
        cumulus_dict[row['sampleid']] = [row['min_umis'], row['min_genes'], row['percent_mito']]
        cellbender_dict[row['sampleid']] = [row['cellbender_expected_cells'], row['cellbender_total_droplets_included']]
        cellranger_dict[row['sampleid']] = [row['introns']]

    logging.info(sample_dict)
    logging.info(mkfastq_dict)
    logging.info(cumulus_dict)
    logging.info(cellbender_dict)

    return {
        'sample': sample_dict,
        'mkfastq': mkfastq_dict,
        'cumulus': cumulus_dict,
        'cellbender': cellbender_dict,
        'cellranger': cellranger_dict
    }


def execute_alto_command(run_alto_file):
    command = "bash %s" % run_alto_file
    logging.info(command)
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    for status_url in result.stdout.decode('utf-8').split("\n"):
        wait_for_terra_submission(status_url)


def wait_for_terra_submission(status_url):
    logging.info("Job status: %s" % status_url)
    entries = status_url.split('/')
    workspace_namespace, workspace_name, submission_id = [entries[idx] for idx in [-4, -3, -1]]
    response = fapi.get_submission(workspace_namespace, workspace_name, submission_id)
    start_time = time.time()
    while response.json()['status'] != 'Done':
        logging.info("Job details: %s \n" % {k: v for k, v in response.json().items()
                                       if k in ['status', 'submissionDate', 'submissionId', '']})
        time.sleep(TERRA_POLL_SPACER)
        response = fapi.get_submission(workspace_namespace, workspace_name, submission_id)
        if time.time() - start_time > TERRA_TIMEOUT:
            logging.info("Terra pipeline took too long to complete.")
            sys.exit()

    for workflow in response.json()['workflows']:
        if workflow['status'] != 'Succeeded':
            logging.info("Terra pipeline failed.")
            sys.exit()

