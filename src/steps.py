import logging
import os
from utils import execute_alto_command, bash_execute_file


def upload_cellranger_mkfastq_input(buckets, directories, sample_tracking, cellranger_version):
    run_id = os.path.basename(sample_tracking['seq_dir'].tolist()[0])
    fastq_flowcell_bucket = "%s/%s_fastqs" % (buckets['fastqs'], run_id)
    fastq_flowcell_dir = "%s/%s" % (directories['fastqs'], run_id)
    os.makedirs(fastq_flowcell_dir, exist_ok=True)

    samplesheet_file = '%s/samplesheet_cellranger_mkfastq.csv' % fastq_flowcell_dir
    samplesheet = sample_tracking[['Lane', 'Sample', 'Index', 'reference', 'chemistry', 'seq_dir']]
    samplesheet.to_csv(samplesheet_file, index=False,
                       header=['Lane', 'Sample', 'Index', 'Reference', 'Chemistry', 'Flowcell'])

    input_cellranger_file = "%s/input_cellranger_mkfastq.json" % fastq_flowcell_dir

    with open(input_cellranger_file, "w") as f:
        f.write("{\n")
        f.write("\t\"cellranger_workflow.input_csv_file\" : \"%s/samplesheet_cellranger_mkfastq.csv\",\n" %
                fastq_flowcell_bucket)
        f.write("\t\"cellranger_workflow.output_directory\" : \"%s\",\n" % buckets['fastqs'])
        f.write("\t\"cellranger_workflow.cellranger_version\" : \"%s\",\n" % cellranger_version)
        f.write("\t\"cellranger_workflow.run_mkfastq\" : true,\n")
        f.write("\t\"cellranger_workflow.run_count\" : false,\n")
        f.write("\t\"cellranger_workflow.mkfastq_docker_registry\" : \"gcr.io/genomics-xavier\"\n")
        f.write("}\n")

    logging.info("STEP 1 | Upload cellranger samplesheet and input file to Google Cloud Storage Bucket. ")
    upload_cellranger_file = "%s/upload_cellranger_mkfastq.sh" % fastq_flowcell_dir
    with open(upload_cellranger_file, "w") as f:
        f.write("gsutil cp %s %s/\n" % (samplesheet_file, fastq_flowcell_bucket))
        f.write("gsutil cp %s %s/\n" % (input_cellranger_file, fastq_flowcell_bucket))
    bash_execute_file(upload_cellranger_file)


def run_cellranger_mkfastq(directories, sample_tracking, alto_workspace, alto_fastqs_folder):
    run_id = os.path.basename(sample_tracking['seq_dir'].iloc[0])
    alto_flowcell_bucket = "%s/%s" % (alto_fastqs_folder, run_id)
    fastq_flowcell_dir = directories['fastqs'] + "/%s" % run_id

    run_alto_file = "%s/run_alto_cellranger_workflow.sh" % fastq_flowcell_dir
    alto_method = "cumulus/cellranger_workflow/28"

    open(run_alto_file, "w").close()
    bash_alto = open(run_alto_file, "a")
    input_cellranger_file = "%s/input_cellranger_mkfastq.json" % fastq_flowcell_dir
    bash_alto.write("alto terra run -m %s -i %s -w %s --bucket-folder %s --no-cache\n" % (
        alto_method, input_cellranger_file, alto_workspace, alto_flowcell_bucket))
    bash_alto.close()

    logging.info("STEP 2 | Initiate Terra cellranger_workflow pipeline via alto. ")
    execute_alto_command(run_alto_file)


def upload_cellranger_count_input(buckets, directories, sample_dicts, sample_tracking, cellranger_version):
    fastqs_bucket = buckets['fastqs']
    counts_bucket = buckets['counts']
    counts_dir = directories['counts']
    sample_dict = sample_dicts['sample']
    mkfastq_dict = sample_dicts['mkfastq']
    cellranger_dict = sample_dicts['cellranger']

    run_id = os.path.basename(sample_tracking['seq_dir'].tolist()[0])
    flowcell = sample_tracking['flowcell'].iloc[0]
    fastq_flowcell_bucket = "%s/%s_fastqs" % (fastqs_bucket, run_id)

    for sample_id in sample_dict.keys():
        os.makedirs("%s/%s" % (counts_dir, sample_id), exist_ok=True)
        samplesheet_cellranger_file = "%s/%s/samplesheet_cellranger.csv" % (counts_dir, sample_id)

        with open(samplesheet_cellranger_file, "w") as f:
            f.write("Sample,Reference,Flowcell,Lane,Index,Chemistry\n")
            for sample in sample_dict[sample_id]:
                fastq_sample_bucket = "%s/fastq_path/%s/" % (fastq_flowcell_bucket, flowcell)
                f.write("%s,%s,%s,%s,%s,%s\n" % (sample, mkfastq_dict[sample][2], fastq_sample_bucket,
                                                 mkfastq_dict[sample][0], mkfastq_dict[sample][1],
                                                 mkfastq_dict[sample][3]))

    for sample_id in sample_dict.keys():
        input_cellranger_file = "%s/%s/input_cellranger.json" % (counts_dir, sample_id)

        with open(input_cellranger_file, "w") as f:
            f.write("{\n")
            f.write("\t\"cellranger_workflow.input_csv_file\" : \"%s/%s/samplesheet_cellranger.csv\",\n" % (
                counts_bucket, sample_id))
            f.write("\t\"cellranger_workflow.output_directory\" : \"%s\",\n" % counts_bucket)
            f.write("\t\"cellranger_workflow.cellranger_version\" : \"%s\",\n" % cellranger_version)
            f.write("\t\"cellranger_workflow.run_mkfastq\" : false,\n")
            f.write("\t\"cellranger_workflow.run_count\" : true,\n")
            f.write("\t\"cellranger_workflow.mkfastq_docker_registry\" : \"gcr.io/genomics-xavier\",\n")
            f.write("\t\"cellranger_workflow.include_introns\" : %s\n" % str(cellranger_dict[sample_id][0]).lower())
            f.write("}\n")

    logging.info("STEP 3 | Upload cellranger samplesheet and input file to Google Cloud Storage Bucket. ")
    uploadcellranger_file = "%s/uploadcellranger_%s.sh" % (counts_dir, flowcell)
    with open(uploadcellranger_file, "w") as f:
        for sample_id in sample_dict.keys():
            samplesheet_cellranger_file = "%s/%s/samplesheet_cellranger.csv" % (counts_dir, sample_id)
            input_cellranger_file = "%s/%s/input_cellranger.json" % (counts_dir, sample_id)
            f.write("gsutil cp %s %s/%s/\n" % (samplesheet_cellranger_file, counts_bucket, sample_id))
            f.write("gsutil cp %s %s/%s/\n" % (input_cellranger_file, counts_bucket, sample_id))
    bash_execute_file(uploadcellranger_file)


def run_cellranger_count(directories, sample_dicts, sample_tracking, alto_workspace, alto_counts_folder):
    sample_dict = sample_dicts['sample']
    counts_dir = directories['counts']

    run_alto_file = "%s/run_alto_cellranger_workflow_%s.sh" % (counts_dir, sample_tracking['flowcell'].iloc[0])
    alto_method = "cumulus/cellranger_workflow/28"

    open(run_alto_file, "w").close()
    bash_alto = open(run_alto_file, "a")
    for sampleid in sample_dict.keys():
        input_cellranger_file = "%s/%s/input_cellranger.json" % (counts_dir, sampleid)
        bash_alto.write("alto terra run -m %s -i %s -w %s --bucket-folder %s/%s --no-cache\n" % (
            alto_method, input_cellranger_file, alto_workspace, alto_counts_folder, sampleid))
    bash_alto.close()

    logging.info("STEP 4 | Initiate Terra cellranger_workflow pipeline via alto. ")
    execute_alto_command(run_alto_file)


def upload_cumulus_samplesheet(buckets, directories, sample_dicts, sample_tracking, count_matrix_name):
    sample_dict = sample_dicts['sample']
    cumulusdict = sample_dicts['cumulus']
    results_dir = directories['results']
    resultsbucket = buckets['results']

    flowcell = sample_tracking['flowcell'].iloc[0]

    for sampleid in sample_dict.keys():
        if not os.path.isdir("%s/%s" % (results_dir, sampleid)):
            os.mkdir("%s/%s" % (results_dir, sampleid))
        samplesheet_cumulus_file = "%s/%s/samplesheet_cumulus.csv" % (results_dir, sampleid)

        with open(samplesheet_cumulus_file, "w") as f:
            f.write("Sample,Location\n")
            for sample in sample_dict[sampleid]:
                f.write("%s,%s/%s/%s\n" % (sample, buckets['counts'], sample, count_matrix_name))

    for sampleid in sample_dict.keys():
        input_cumulus_file = "%s/%s/input_cumulus.json" % (results_dir, sampleid)
        samplesheet_cumulus = "%s/%s/samplesheet_cumulus.csv" % (resultsbucket, sampleid)

        with open('templates/cumulus_input_template.json') as f:
            template = f.read()
        template = template.replace('{input_file}', samplesheet_cumulus) \
            .replace('{output_directory}', "%s/" % resultsbucket) \
            .replace('{output_name}', sampleid) \
            .replace('"{min_umis}"', str(cumulusdict[sampleid][0])) \
            .replace('"{min_genes}"', str(cumulusdict[sampleid][1])) \
            .replace('"{percent_mito}"', str(cumulusdict[sampleid][2]))

        with open(input_cumulus_file, "w") as f:
            f.write(template)

    logging.info("STEP 5 | Upload cumulus samplesheet and input file to Google Cloud Storage Bucket. ")
    upload_cumulus_file = "%s/uploadcumulus_%s.sh" % (results_dir, flowcell)
    with open(upload_cumulus_file, "w") as f:
        for sampleid in sample_dict.keys():
            samplesheet_cumulus_file = "%s/%s/samplesheet_cumulus.csv" % (results_dir, sampleid)
            input_cumulus_file = "%s/%s/input_cumulus.json" % (results_dir, sampleid)
            f.write("gsutil cp %s %s/%s/\n" % (samplesheet_cumulus_file, resultsbucket, sampleid))
            f.write("gsutil cp %s %s/%s/\n" % (input_cumulus_file, resultsbucket, sampleid))
    bash_execute_file(upload_cumulus_file)


def run_cumulus(directories, sample_dicts, sample_tracking, alto_workspace, alto_results_folder):
    sample_dict = sample_dicts['sample']
    results_dir = directories['results']

    run_alto_file = "%s/run_alto_cumulus_%s.sh" % (results_dir, sample_tracking['flowcell'].iloc[0])
    alto_method = "cumulus/cumulus/43"

    open(run_alto_file, "w").close()
    bash_alto = open(run_alto_file, "a")
    for sampleid in sample_dict.keys():
        input_cumulus_file = "%s/%s/input_cumulus.json" % (results_dir, sampleid)
        bash_alto.write("alto terra run -m %s -i %s -w %s --bucket-folder %s/%s --no-cache\n" % (
            alto_method, input_cumulus_file, alto_workspace, alto_results_folder, sampleid))
    bash_alto.close()

    logging.info("STEP 6 | Initiate Terra cumulus pipeline via alto. ")
    execute_alto_command(run_alto_file)


def upload_cell_bender_input(buckets, directories, sample_dicts, sample_tracking, count_matrix_name):
    sample_dict = sample_dicts['sample']
    cellbenderdict = sample_dicts['cellbender']
    cellbender_dir = directories['cellbender']
    cellbenderbucket = buckets['cellbender']
    countsbucket = buckets['counts']

    for sampleid in sample_dict.keys():
        if not os.path.isdir("%s/%s" % (cellbender_dir, sampleid)):
            os.mkdir("%s/%s" % (cellbender_dir, sampleid))

        for sample in sample_dict[sampleid]:
            if not os.path.isdir("%s/%s" % (cellbender_dir, sampleid)):
                os.mkdir("%s/%s" % (cellbender_dir, sampleid))
            input_cellbender_file = "%s/%s/input_cellbender.json" % (cellbender_dir, sampleid)
            with open('templates/cellbender_input_template.json') as f:
                template = f.read()
            template = template.replace('"{total_droplets_included}"', str(cellbenderdict[sampleid][1])) \
                .replace('"{expected_cells}"', str(cellbenderdict[sampleid][0])) \
                .replace('{sample_name}', str(sampleid)) \
                .replace('{input_dir}', "%s/%s/%s" % (countsbucket, sampleid, count_matrix_name)) \
                .replace('{output_dir}', "%s/%s" % (cellbenderbucket, sampleid))

            with open(input_cellbender_file, "w") as f:
                f.write(template)

    logging.info("STEP 7 | Upload cellbender input file to Google Cloud Storage Bucket. ")
    uploadcellbender_file = "%s/uploadcellbender_%s.sh" % (cellbender_dir, sample_tracking['flowcell'].iloc[0])
    with open(uploadcellbender_file, "w") as f:
        for sampleid in sample_dict.keys():
            for sample in sample_dict[sampleid]:
                input_cellbender_file = "%s/%s/input_cellbender.json" % (cellbender_dir, sampleid)
                f.write("gsutil cp %s %s/%s/\n" % (input_cellbender_file, cellbenderbucket, sampleid))
    bash_execute_file(uploadcellbender_file)


def run_cellbender(directories, sample_dicts, sample_tracking, alto_workspace, alto_cellbender_folder):
    sample_dict = sample_dicts['sample']
    cellbender_dir = directories['cellbender']

    run_alto_file = "%s/run_alto_cellbender_%s.sh" % (cellbender_dir, sample_tracking['flowcell'].iloc[0])
    alto_method = "cellbender/remove-background/11"

    open(run_alto_file, "w").close()
    bash_alto = open(run_alto_file, "a")
    for sampleid in sample_dict.keys():
        for sample in sample_dict[sampleid]:
            input_cellbender_file = "%s/%s/input_cellbender.json" % (cellbender_dir, sampleid)
            bash_alto.write("alto terra run -m %s -i %s -w %s --bucket-folder %s/%s --no-cache\n" % (
                alto_method, input_cellbender_file, alto_workspace, alto_cellbender_folder, sampleid))
    bash_alto.close()

    logging.info("STEP 8 | Initiate Terra remove-background pipeline via alto. ")
    execute_alto_command(run_alto_file)


def upload_post_cellbender_cumulus_input(buckets, directories, sample_dicts, sample_tracking, cellbender_matrix_name):
    sample_dict = sample_dicts['sample']
    cumulusdict = sample_dicts['cumulus']
    cellbenderbucket = buckets['cellbender']
    cellbender_resultsbucket = buckets['cellbender_results']
    cellbender_results_dir = directories['cellbender_results']

    for sampleid in sample_dict.keys():
        if not os.path.isdir("%s/%s" % (cellbender_results_dir, sampleid)):
            os.mkdir("%s/%s" % (cellbender_results_dir, sampleid))
        samplesheet_cellbender_cumulus_file = "%s/%s/samplesheet_cellbender_cumulus.csv" % (
            cellbender_results_dir, sampleid)

        with open(samplesheet_cellbender_cumulus_file, "w") as f:
            f.write("Sample,Location\n")
            for sample in sample_dict[sampleid]:
                f.write("%s,%s/%s/%s/%s_%s\n" % (
                    sample, cellbenderbucket, sampleid, sampleid, sampleid, cellbender_matrix_name))

    for sampleid in sample_dict.keys():
        input_cellbender_cumulus_file = "%s/%s/input_cumulus.json" % (cellbender_results_dir, sampleid)
        samplesheet_cellbender = "%s/%s/samplesheet_cellbender_cumulus.csv" % (cellbender_resultsbucket, sampleid)

        with open('templates/cumulus_input_template.json') as f:
            template = f.read()
        template = template.replace('{input_file}', samplesheet_cellbender) \
            .replace('{output_directory}', "%s/" % cellbender_resultsbucket) \
            .replace('{output_name}', sampleid) \
            .replace('"{min_umis}"', str(cumulusdict[sampleid][0])) \
            .replace('"{min_genes}"', str(cumulusdict[sampleid][1])) \
            .replace('"{percent_mito}"', str(cumulusdict[sampleid][2])) \

        with open(input_cellbender_cumulus_file, "w") as f:
            f.write(template)

    logging.info("STEP 9 | Upload post-cellbender cumulus samplesheet and input file to Google Cloud Storage Bucket. ")
    uploadcellbendercumulus_file = "%s/uploadcellbendercumulus_%s.sh" % (
        cellbender_results_dir, sample_tracking['flowcell'].iloc[0])
    with open(uploadcellbendercumulus_file, "w") as f:
        for sampleid in sample_dict.keys():
            samplesheet_cellbender_cumulus_file = "%s/%s/samplesheet_cellbender_cumulus.csv" % (
                cellbender_results_dir, sampleid)
            input_cellbender_cumulus_file = "%s/%s/input_cumulus.json" % (cellbender_results_dir, sampleid)
            f.write("gsutil cp %s %s/%s/\n" % (samplesheet_cellbender_cumulus_file, cellbender_resultsbucket, sampleid))
            f.write("gsutil cp %s %s/%s/\n" % (input_cellbender_cumulus_file, cellbender_resultsbucket, sampleid))
    bash_execute_file(uploadcellbendercumulus_file)


def run_cumulus_post_cellbender(directories, sample_dicts, sample_tracking, alto_workspace, alto_results_folder):
    sample_dict = sample_dicts['sample']
    cellbender_results_dir = directories['cellbender_results']

    run_alto_file = "%s/run_alto_cellbender_cumulus_%s.sh" % (cellbender_results_dir, sample_tracking['flowcell'].iloc[0])
    alto_method = "cumulus/cumulus/43"

    open(run_alto_file, "w").close()
    bash_alto = open(run_alto_file, "a")
    for sampleid in sample_dict.keys():
        input_cellbender_cumulus_file = "%s/%s/input_cumulus.json" % (cellbender_results_dir, sampleid)
        bash_alto.write("alto terra run -m %s -i %s -w %s --bucket-folder %s/%s --no-cache\n" % (
            alto_method, input_cellbender_cumulus_file, alto_workspace, alto_results_folder, sampleid))
    bash_alto.close()

    logging.info("STEP 10 | Initiate Terra cumulus pipeline via alto. ")
    execute_alto_command(run_alto_file)
