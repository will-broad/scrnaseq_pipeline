import logging
import shutil
import sys
import os
import subprocess
import re
import time
import firecloud.api as fapi

TERRA_POLL_SPACER = 600  # 10 minutes
TERRA_TIMEOUT = 7200  # 2 hours


def upload_cell_ranger_samplesheet_and_input(buckets, directories, sample_dicts, cellranger_version):
    bcl_bucket = buckets['bcl']
    counts_bucket = buckets['counts']
    counts_dir = directories['counts']
    sample_dict = sample_dicts['sample']
    mkfastq_dict = sample_dicts['mkfastq']
    cellranger_dict = sample_dicts['cellranger']

    for sampleid in sample_dict.keys():
        if not os.path.isdir("%s/%s" % (counts_dir, sampleid)):
            os.mkdir("%s/%s" % (counts_dir, sampleid))
        samplesheet_cellranger_file = "%s/%s/samplesheet_cellranger.csv" % (counts_dir, sampleid)

        with open(samplesheet_cellranger_file, "w") as f:
            f.write("Sample,Reference,Flowcell,Lane,Index,Chemistry\n")
            for sample in sample_dict[sampleid]:
                lane = mkfastq_dict[sample][0]
                index = mkfastq_dict[sample][1]
                reference = mkfastq_dict[sample][2]
                chemistry = mkfastq_dict[sample][3]
                f.write("%s,%s,%s,%s,%s,%s\n" % (sample, reference, bcl_bucket, lane, index, chemistry))

    for sampleid in sample_dict.keys():
        input_cellranger_file = "%s/%s/input_cellranger.json" % (counts_dir, sampleid)

        with open(input_cellranger_file, "w") as f:
            f.write("{\n")
            f.write("\t\"cellranger_workflow.input_csv_file\" : \"%s/%s/samplesheet_cellranger.csv\",\n" % (
                counts_bucket, sampleid))
            f.write("\t\"cellranger_workflow.output_directory\" : \"%s\",\n" % (counts_bucket))
            f.write("\t\"cellranger_workflow.cellranger_version\" : \"%s\",\n" % (cellranger_version))
            f.write("\t\"cellranger_workflow.run_mkfastq\" : true,\n")
            f.write("\t\"cellranger_workflow.mkfastq_docker_registry\" : \"quay.io/cumulus\",\n")
            f.write("\t\"cellranger_workflow.include_introns\" : %s\n" % str(cellranger_dict[sampleid][0]).lower())
            f.write("}\n")

    # Running bash script below to upload cellranger samplesheet and input file to Google Cloud Storage Bucket.
    logging.info("\n## STEP 1 | Upload cellranger samplesheet and input file to Google Cloud Storage Bucket. ##")
    uploadcellranger_file = "%s/uploadcellranger.sh" % counts_dir
    with open(uploadcellranger_file, "w") as f:
        for sampleid in sample_dict.keys():
            samplesheet_cellranger_file = "%s/%s/samplesheet_cellranger.csv" % (counts_dir, sampleid)
            input_cellranger_file = "%s/%s/input_cellranger.json" % (counts_dir, sampleid)
            f.write("gsutil cp %s %s/%s/\n" % (samplesheet_cellranger_file, counts_bucket, sampleid))
            f.write("gsutil cp %s %s/%s/\n" % (input_cellranger_file, counts_bucket, sampleid))
    command = "bash %s" % uploadcellranger_file
    logging.info(command)
    subprocess.run(command, shell=True, stdout=sys.stdout, stderr=sys.stderr, check=True)


def run_cell_ranger_mkfastq_and_count(directories, sample_dicts, alto_workspace, alto_counts_folder):
    sampledict = sample_dicts['sample']
    counts_dir = directories['counts']

    run_alto_file = "%s/run_alto_cellranger_workflow.sh" % (counts_dir)
    alto_method = "cumulus/cellranger_workflow/28"

    open(run_alto_file, "w").close()
    bash_alto = open(run_alto_file, "a")
    for sampleid in sampledict.keys():
        input_cellranger_file = "%s/%s/input_cellranger.json" % (counts_dir, sampleid)
        bash_alto.write("alto terra run -m %s -i %s -w %s --bucket-folder %s/%s --no-cache\n" % (
            alto_method, input_cellranger_file, alto_workspace, alto_counts_folder, sampleid))
    bash_alto.close()

    logging.info("\n## STEP 2 | Initiate Terra cellranger_workflow pipeline via alto. ##")
    command = "bash %s" % run_alto_file
    logging.info(command)
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    for status_url in result.stdout.decode('utf-8').split("\n"):
        wait_for_terra_submission(status_url)


def upload_cumulus_samplesheet(buckets, directories, sample_dicts, sampletracking, count_matrix_name):
    sampledict = sample_dicts['sample']
    cumulusdict = sample_dicts['cumulus']
    results_dir = directories['results']
    countsbucket = buckets['counts']
    resultsbucket = buckets['results']

    for sampleid in sampledict.keys():
        if not os.path.isdir("%s/%s" % (results_dir, sampleid)):
            os.mkdir("%s/%s" % (results_dir, sampleid))
        samplesheet_cumulus_file = "%s/%s/samplesheet_cumulus.csv" % (results_dir, sampleid)

        with open(samplesheet_cumulus_file, "w") as f:
            f.write("Sample,Location\n")
            for sample in sampledict[sampleid]:
                f.write("%s,%s/%s/%s\n" % (sample, countsbucket, sample, count_matrix_name))

    # Make input_cumulus file for cumulus.
    for sampleid in sampledict.keys():
        input_cumulus_file = "%s/%s/input_cumulus.json" % (results_dir, sampleid)

        with open(input_cumulus_file, "w") as f:
            f.write("{\n")
            f.write("\t\"cumulus.input_file\" : \"%s/%s/samplesheet_cumulus.csv\",\n" % (resultsbucket, sampleid))
            f.write("\t\"cumulus.output_directory\" : \"%s/\",\n" % (resultsbucket))
            # f.write("\t\"cumulus.default_reference\" : \"%s\",\n" % reference)
            f.write("\t\"cumulus.output_name\" : \"%s\",\n" % (sampleid))
            f.write("\t\"cumulus.min_umis\" : %s,\n" % cumulusdict[sampleid][0])
            f.write("\t\"cumulus.min_genes\" : %s,\n" % cumulusdict[sampleid][1])
            f.write("\t\"cumulus.percent_mito\" : %s,\n" % cumulusdict[sampleid][2])
            f.write("\t\"cumulus.infer_doublets\" : true,\n")

            f.write("\t\"cumulus.run_louvain\" : false,\n")
            f.write("\t\"cumulus.run_leiden\" : true,\n")
            f.write("\t\"cumulus.leiden_resolution\" : 1,\n")
            f.write("\t\"cumulus.run_diffmap\" : false,\n")
            f.write("\t\"cumulus.perform_de_analysis\" : true,\n")
            f.write("\t\"cumulus.cluster_labels\" : \"leiden_labels\",\n")
            f.write("\t\"cumulus.annotate_cluster\" : false,\n")
            f.write("\t\"cumulus.fisher\" : true,\n")
            f.write("\t\"cumulus.t_test\" : true,\n")
            f.write("\t\"cumulus.find_markers_lightgbm\" : false,\n")

            f.write("\t\"cumulus.run_tsne\" : false,\n")
            f.write("\t\"cumulus.run_umap\" : true,\n")
            f.write("\t\"cumulus.umap_K\" : 15,\n")
            f.write("\t\"cumulus.umap_min_dist\" : 0.5,\n")
            f.write("\t\"cumulus.umap_spread\" : 1,\n")
            f.write("\t\"cumulus.plot_umap\" : \"leiden_labels\",\n")
            # f.write("\t\"cumulus.plot_diffmap\" : \"leiden_labels\",\n")
            f.write("\t\"cumulus.output_h5ad\" : true\n")
            f.write("}\n")

    # Running bash script below to upload cumulus samplesheet and input file to Google Cloud Storage Bucket.
    logging.info("\n## STEP 3 | Upload cumulus samplesheet and input file to Google Cloud Storage Bucket. ##")
    uploadcumulus_file = "%s/uploadcumulus_%s.sh" % (results_dir, sampletracking['flowcell'].iloc[0])
    with open(uploadcumulus_file, "w") as f:
        for sampleid in sampledict.keys():
            samplesheet_cumulus_file = "%s/%s/samplesheet_cumulus.csv" % (results_dir, sampleid)
            input_cumulus_file = "%s/%s/input_cumulus.json" % (results_dir, sampleid)
            f.write("gsutil cp %s %s/%s/\n" % (samplesheet_cumulus_file, resultsbucket, sampleid))
            f.write("gsutil cp %s %s/%s/\n" % (input_cumulus_file, resultsbucket, sampleid))
            # f.write("gsutil cp %s %s/\n" % (cumulusdict[sampleid][5], resultsbucket))
    command = "bash %s" % uploadcumulus_file
    logging.info(command)
    subprocess.run(command, shell=True, stdout=sys.stdout, stderr=sys.stderr, check=True)


def run_cumulus(directories, sample_dicts, alto_workspace, alto_results_folder):
    sampledict = sample_dicts['sample']
    results_dir = directories['results']

    run_alto_file = "%s/run_alto_cumulus.sh" % (results_dir)
    alto_method = "cumulus/cumulus/43"

    open(run_alto_file, "w").close()
    bash_alto = open(run_alto_file, "a")
    for sampleid in sampledict.keys():
        input_cumulus_file = "%s/%s/input_cumulus.json" % (results_dir, sampleid)
        bash_alto.write("alto terra run -m %s -i %s -w %s --bucket-folder %s/%s --no-cache\n" % (
            alto_method, input_cumulus_file, alto_workspace, alto_results_folder, sampleid))
    bash_alto.close()

    # Terminal commands to run alto cumulus bash script.
    logging.info(
        "\n## STEP 4 | Initiate Terra cumulus pipeline via alto. ##")
    command = "bash %s" % run_alto_file
    logging.info(command)
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    for status_url in result.stdout.decode('utf-8').split("\n"):
        wait_for_terra_submission(status_url)


def upload_cell_bender_input(buckets, directories, sample_dicts, sampletracking, count_matrix_name):
    sampledict = sample_dicts['sample']
    cellbenderdict = sample_dicts['cellbender']
    cellbender_dir = directories['cellbender']
    cellbenderbucket = buckets['cellbender']
    countsbucket = buckets['counts']
    # Make input_cellbender file for cellbender.
    for sampleid in sampledict.keys():
        if not os.path.isdir("%s/%s" % (cellbender_dir, sampleid)):
            os.mkdir("%s/%s" % (cellbender_dir, sampleid))

        for sample in sampledict[sampleid]:
            if not os.path.isdir("%s/%s" % (cellbender_dir, sampleid)):
                os.mkdir("%s/%s" % (cellbender_dir, sampleid))
            input_cellbender_file = "%s/%s/input_cellbender.json" % (cellbender_dir, sampleid)

            with open(input_cellbender_file, "w") as f:
                f.write("{\n")
                # f.write("\t\"cellbender_remove_background.cellbender_remove_background_gpu.z_layers\" : \"\",\n"),
                f.write(
                    "\t\"cellbender_remove_background.run_cellbender_remove_background_gpu.total_droplets_included\" : %s,\n" %
                    cellbenderdict[sampleid][1]),
                f.write("\t\"cellbender_remove_background.run_cellbender_remove_background_gpu.z_dim\" : 100,\n"),
                f.write("\t\"cellbender_remove_background.run_cellbender_remove_background_gpu.epochs\" : 150,\n"),
                f.write(
                    "\t\"cellbender_remove_background.run_cellbender_remove_background_gpu.expected_cells\" : %s,\n" %
                    cellbenderdict[sampleid][0]),
                f.write(
                    "\t\"cellbender_remove_background.run_cellbender_remove_background_gpu.sample_name\" : \"%s\",\n" % sampleid)
                f.write(
                    "\t\"cellbender_remove_background.run_cellbender_remove_background_gpu.hardware_preemptible_tries\" : 0,\n"),
                f.write(
                    "\t\"cellbender_remove_background.run_cellbender_remove_background_gpu.input_10x_h5_file_or_mtx_directory\" : \"%s/%s/%s\",\n" % (
                        countsbucket, sampleid, count_matrix_name))
                f.write(
                    "\t\"cellbender_remove_background.run_cellbender_remove_background_gpu.output_directory\" : \"%s/%s\",\n" % (
                        cellbenderbucket, sampleid))
                f.write(
                    "\t\"cellbender_remove_background.run_cellbender_remove_background_gpu.learning_rate\" : 0.00005,\n")
                f.write(
                    "\t\"cellbender_remove_background.run_cellbender_remove_background_gpu.fpr\" : \"0.01 0.05 0.1\"\n")
                f.write("}\n")

    # Running bash script below to upload cellbender input file to Google Cloud Storage Bucket.
    logging.info("\n## STEP 5 | Upload cellbender input file to Google Cloud Storage Bucket. ##")
    uploadcellbender_file = "%s/uploadcellbender_%s.sh" % (cellbender_dir, sampletracking['flowcell'].iloc[0])
    with open(uploadcellbender_file, "w") as f:
        for sampleid in sampledict.keys():
            for sample in sampledict[sampleid]:
                input_cellbender_file = "%s/%s/input_cellbender.json" % (cellbender_dir, sampleid)
                f.write("gsutil cp %s %s/%s/\n" % (input_cellbender_file, cellbenderbucket, sampleid))
    command = "bash %s" % uploadcellbender_file
    logging.info(command)
    subprocess.run(command, shell=True, stdout=sys.stdout, stderr=sys.stderr, check=True)


def run_cellbender(directories, sample_dicts, alto_workspace, alto_cellbender_folder):
    sampledict = sample_dicts['sample']
    cellbender_dir = directories['cellbender']

    run_alto_file = "%s/run_alto_cellbender.sh" % (cellbender_dir)
    alto_method = "cellbender/remove-background/11"

    open(run_alto_file, "w").close()
    bash_alto = open(run_alto_file, "a")
    for sampleid in sampledict.keys():
        for sample in sampledict[sampleid]:
            input_cellbender_file = "%s/%s/input_cellbender.json" % (cellbender_dir, sampleid)
            bash_alto.write("alto terra run -m %s -i %s -w %s --bucket-folder %s/%s --no-cache\n" % (
                alto_method, input_cellbender_file, alto_workspace, alto_cellbender_folder, sampleid))
    bash_alto.close()

    # Terminal commands to run alto cumulus bash script.
    logging.info("\n## STEP 6 | Initiate Terra remove-background pipeline via alto. ##")
    command = "bash %s" % run_alto_file
    logging.info(command)
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    for status_url in result.stdout.decode('utf-8').split("\n"):
        wait_for_terra_submission(status_url)


def upload_post_cellbender_cumulus_input(buckets, directories, sample_dicts, sampletracking, cellbender_matrix_name):
    sampledict = sample_dicts['sample']
    cumulusdict = sample_dicts['cumulus']
    cellbenderbucket = buckets['cellbender']
    cellbender_resultsbucket = buckets['cellbender_results']
    cellbender_results_dir = directories['cellbender_results']

    for sampleid in sampledict.keys():
        if not os.path.isdir("%s/%s" % (cellbender_results_dir, sampleid)):
            os.mkdir("%s/%s" % (cellbender_results_dir, sampleid))
        samplesheet_cellbender_cumulus_file = "%s/%s/samplesheet_cellbender_cumulus.csv" % (
            cellbender_results_dir, sampleid)

        with open(samplesheet_cellbender_cumulus_file, "w") as f:
            f.write("Sample,Location\n")
            for sample in sampledict[sampleid]:
                f.write("%s,%s/%s/%s/%s_%s\n" % (
                    sample, cellbenderbucket, sampleid, sampleid, sampleid, cellbender_matrix_name))

        # Make input_cumulus file for cumulus.
    for sampleid in sampledict.keys():
        input_cellbender_cumulus_file = "%s/%s/input_cumulus.json" % (cellbender_results_dir, sampleid)

        with open(input_cellbender_cumulus_file, "w") as f:
            f.write("{\n")
            f.write("\t\"cumulus.input_file\" : \"%s/%s/samplesheet_cellbender_cumulus.csv\",\n" % (
                cellbender_resultsbucket, sampleid))
            f.write("\t\"cumulus.output_directory\" : \"%s/\",\n" % (cellbender_resultsbucket))
            # f.write("\t\"cumulus.default_reference\" : \"%s\",\n" % reference)
            f.write("\t\"cumulus.output_name\" : \"%s\",\n" % (sampleid))
            f.write("\t\"cumulus.min_umis\" : %s,\n" % cumulusdict[sampleid][0])
            f.write("\t\"cumulus.min_genes\" : %s,\n" % cumulusdict[sampleid][1])
            f.write("\t\"cumulus.percent_mito\" : %s,\n" % cumulusdict[sampleid][2])
            f.write("\t\"cumulus.infer_doublets\" : true,\n")

            f.write("\t\"cumulus.run_louvain\" : false,\n")
            f.write("\t\"cumulus.run_leiden\" : true,\n")
            f.write("\t\"cumulus.leiden_resolution\" : 1,\n")
            f.write("\t\"cumulus.run_diffmap\" : false,\n")
            f.write("\t\"cumulus.perform_de_analysis\" : true,\n")
            f.write("\t\"cumulus.cluster_labels\" : \"leiden_labels\",\n")
            f.write("\t\"cumulus.annotate_cluster\" : false,\n")
            f.write("\t\"cumulus.fisher\" : true,\n")
            f.write("\t\"cumulus.t_test\" : true,\n")
            f.write("\t\"cumulus.find_markers_lightgbm\" : false,\n")

            f.write("\t\"cumulus.run_tsne\" : false,\n")
            f.write("\t\"cumulus.run_umap\" : true,\n")
            f.write("\t\"cumulus.umap_K\" : 15,\n")
            f.write("\t\"cumulus.umap_min_dist\" : 0.5,\n")
            f.write("\t\"cumulus.umap_spread\" : 1,\n")
            f.write("\t\"cumulus.plot_umap\" : \"leiden_labels\",\n")
            # f.write("\t\"cumulus.plot_diffmap\" : \"leiden_labels\",\n")
            f.write("\t\"cumulus.output_h5ad\" : true\n")
            f.write("}\n")

        # Running bash script below to upload cumulus samplesheet and input file to Google Cloud Storage Bucket.
    logging.info("\n## STEP 7 | Upload post-cellbender cumulus samplesheet and input file to Google Cloud Storage Bucket. ##")
    uploadcellbendercumulus_file = "%s/uploadcellbendercumulus_%s.sh" % (
        cellbender_results_dir, sampletracking['flowcell'].iloc[0])
    with open(uploadcellbendercumulus_file, "w") as f:
        for sampleid in sampledict.keys():
            samplesheet_cellbender_cumulus_file = "%s/%s/samplesheet_cellbender_cumulus.csv" % (
                cellbender_results_dir, sampleid)
            input_cellbender_cumulus_file = "%s/%s/input_cumulus.json" % (cellbender_results_dir, sampleid)
            f.write("gsutil cp %s %s/%s/\n" % (samplesheet_cellbender_cumulus_file, cellbender_resultsbucket, sampleid))
            f.write("gsutil cp %s %s/%s/\n" % (input_cellbender_cumulus_file, cellbender_resultsbucket, sampleid))
            # f.write("gsutil cp %s %s/\n" % (cumulusdict[sampleid][5], cellbender_resultsbucket))
    command = "bash %s" % uploadcellbendercumulus_file
    logging.info(command)
    subprocess.run(command, shell=True, stdout=sys.stdout, stderr=sys.stderr, check=True)


def run_cumulus_post_cellbender(directories, sample_dicts, alto_workspace, alto_results_folder):
    sampledict = sample_dicts['sample']
    cellbender_results_dir = directories['cellbender_results']

    # Write bash script below to run alto to kick off cumulus jobs from command line to Terra.
    run_alto_file = "%s/run_alto_cellbender_cumulus.sh" % (cellbender_results_dir)
    alto_method = "cumulus/cumulus/43"

    open(run_alto_file, "w").close()
    bash_alto = open(run_alto_file, "a")
    for sampleid in sampledict.keys():
        input_cellbender_cumulus_file = "%s/%s/input_cumulus.json" % (cellbender_results_dir, sampleid)
        bash_alto.write("alto terra run -m %s -i %s -w %s --bucket-folder %s/%s --no-cache\n" % (
            alto_method, input_cellbender_cumulus_file, alto_workspace, alto_results_folder, sampleid))
    bash_alto.close()

    # Terminal commands to run alto cumulus bash script.
    logging.info("\n## STEP 8 | Initiate Terra cumulus pipeline via alto. ##")
    command = "bash %s" % run_alto_file
    logging.info(command)
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    for status_url in result.stdout.decode('utf-8').split("\n"):
        wait_for_terra_submission(status_url)


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


def wait_for_terra_submission(status_url):
    logging.info("Job status: %s" % status_url)
    entries = status_url.split('/')
    workspace_namespace, workspace_name, submission_id = [entries[idx] for idx in [-4, -3, -1]]
    response = fapi.get_submission(workspace_namespace, workspace_name, submission_id)
    start_time = time.time()
    while response.json()['status'] != 'Done':
        logging.info({k: v for k, v in response.json().items() if k in ['status', 'submissionDate', 'submissionId', '']})
        logging.info('\n')
        time.sleep(TERRA_POLL_SPACER)
        response = fapi.get_submission(workspace_namespace, workspace_name, submission_id)
        if time.time() - start_time > TERRA_TIMEOUT:
            raise RuntimeError("Terra pipeline took too long to complete.")

    for workflow in response.json()['workflows']:
        if workflow['status'] != 'Succeeded':
            raise RuntimeError("Terra pipeline failed.")


# gsutil hash local-file
#
# gsutil ls -L gs://genomics/genotypes.vcf
#

def gcp_copy(src, recursive, parallel, ionice=True):
    call_args = ['ionice', '-c', '2', '-n', '7'] if ionice and (shutil.which('ionice') is not None) else []
    call_args += ['gsutil', '-o', 'GSUtil:parallel_composite_upload_threshold=150M']
    if parallel:
        call_args.append('-m')
    call_args.append('cp')
    if recursive:
        call_args.append('-r')
    call_args.extend(src)
    logging.info(' '.join(call_args))
    subprocess.check_call(call_args)
