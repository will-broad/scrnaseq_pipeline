# Make mkfastq, cellranger_workflow, and cumulus (pegasus) files for running in Terra

Date: 2021/07/07

Author: Orr Ashenberg & Caroline Porter

This script creates the `mkfastq` script for running Cell Ranger `mkfastq` locally on Broad UGER to generate `fastq` files from `bcl` files. It then uploads the `fastq` files to your Google Cloud Storage Bucket. Next, the script creates the files for running `cellranger_workflow` and `cumulus` pipelines on Terra and uploads them to your workspace. The user must specify all the input settings in the first code cell of this notebook, including local UGER directories and Google Cloud Buckets, and the user must create the sample tracking file that records information on all their samples. No other code cells need to be modified, unless you want to change settings for running any of the pipelines. When running this script as a jupyter notebook, terminal commands to copy files to and from the Google Cloud Storage buckets are printed as output from the code cells. When running this script as a `python` script from your terminal, these commands are written to the standard out of your terminal. This code was originally written to process HTAPP samples, but has been modified to process other samples with different organizational conventions.

This code is written to process all the samples listed in a sample sheet containing information on all your samples. The code can process multiple biological samples coming from a sample tracking file. Individual count matrices are made for each 10x channel by `cellranger_workflow`.
**Sample tracking file**

The sample tracking file, in csv format, is a useful way to track the important information for each sample, and is needed to run this script. Each sample requires the following text fields.
- date: The date your samples are processed in yyyy_mm_dd format.
- run_pipeline: Boolean (True or False) that determines what samples are processed. Set this to True for all samples you want to processs. All other samples must be set to False. How this works in operation is that as you add your new samples, set them to run_pipeline = True and set the previously run samples to run_pipeline = False. Remember that all samples that are processed together must come from the same flow cell. The code is written to only process one flow cell!
- Channel Name: This is the sample name that is used by the experimental team to name a 10x channel.
- sampleid: This is the sample id.
- condition: Any biological or technical condition used in collecting this sample. This could be a buffer used or a flow cytometry sorting gate. If there is no special condition, label this as none.
- tissue: The tissue of origin. This column is optional.
- replicate: This is used to designate which 10x channel (up to 8 different channels on a Chromium chip) this sample was run on, and is useful when multiple 10x channels are run for the same biological sample. The channel number must be an integer but it does not matter what integers you choose, as long as different channels use different integers. I suggest 1, 2, 3... If there is only a single channel, label this as channel1.
- Lane: The lane that the sample was sequenced on within the flowcell. It can be a single lane (ex: 5), several lanes (ex: 5-6), or * (all lanes on the flow cell).
- Index: The 10x index for the sample.
- project: The name of the project you'd like to see attached to your directories
- reference: The genome reference to use when Cell Ranger `count` is creating the counts matrices. Please choose from one of references listed in Cumulus read the docs.
- chemistry: The sequencing chemistry used.
- flowcell: The flowcell id from your sequencing run.
- seq_dir: The directory of your sequencing results.
- min_umis: the min number of UMIs you'd like to use for filtering when you run cumulus pegasus.
- min_genes: the min number of genes you'd like to use for filtering when you run cumulus pegasus.
- percent_mito: the max percentage of expression coming from mito genes that you'd like to set for filtering when you run cumulus pegasus.
- focus: the genome you would like to focus on if you are are using a mixed-species genome. The analysis will be performed on alignments to this genome.
- append: the genome you'd like to append to your counts matrix. These counts will not be included in the main analysis workflow.
- calc_signature_scores: a path to a .gmt file you can use for testing gene signatures using cumulus pegasus.

The input cell also requires the user to specify the location of a Cell Ranger `mkfastq` sample sheet template, that the script will modify with the appropriate settings. Please use the path for the template listed below, or make a local copy of the template in your file system.
```
/ahg/regevdata/users/orr/code/cellranger/cellranger_mkfastq_2.1.0.sh
```

**Setting up Google Cloud authorization, Terra workspaces, and cellranger_workflow and cumulus pipelines**

Follow the [instructions here](https://cumulus.readthedocs.io/en/latest/) to set up Google Cloud authorization. This only needs to be done a single time. When setting up your Terra workspace, Joshua Gould will assist you. You need both writer permission and computes permission to write data and to run the computational pipelines.

## Terra KCO cellranger_mkfastq_count pipeline and Terra KCO cumulus pipeline
The directions for the KCO `cellranger_workflow` pipeline are located in https://cumulus.readthedocs.io/en/latest/. When you run this pipeline, at that point Cell Ranger `mkfastq` has already been run to generate `fastq` files, although it is possible to use this pipeline to also run `mkfastq`.

After the count matrices are generated, we prepare the files to run the `cumulus` pipeline. These contain sample metadata and paths to the count matrices. The directions for the KCO `cumulus` pipeline are located in https://cumulus.readthedocs.io/en/latest/)

Importing the pipelines only needs to be done once in the processed data workspace. To import the pipelines, do the following:
- Go to Method Configurations.
- Import Configuration.
- Import from Method Repository.
- Search for `cellranger_workflow` or `cumulus` and Select Configuration.
- Use Blank Configuration.
- Select Name to be `cellranger_workflow` or `cumulus` and Root Entity Type to be participant.
- Import Method.

To run the pipelines in the Terra workspace, do the following:
- Select Method Configurations, select `cellranger_workflow` or `cumulus`, select Edit Configuration.
- Uncheck the box for Configure inputs/outputs using the Workspace Data Model.
- Unceck "use call caching"
- Click Populate with a .json file, upload the `json` file from your local computer, and verify the text field inputs are filled as expected. Ensure all previous text field inputs (from any earlier runs) have been cleared after uploading the `json` file.
- Select Save and then Launch Analysis.
```
use Anaconda3
python /ahg/regevdata/users/orr/code/cellranger/make_firecloud_V2.py
```
The first few lines that are printed to the terminal are visual checks that the sample and its information, such as lane and index, are being parsed correctly by the script. Next, you submit a bash script `run_mkfastq_uploadfastq.sh` that runs Cell Ranger `mkfastq`, and when that is done, it uploads the `fastq` files to the Google Cloud Storage Bucket. All input and json files for `cellranger_mkfastq_count` and `cumulus` are uploaded automatically to the Google Cloud, so once the `fastq` files are uploaded, those pipelines can be run sequentially. Finally, the count matrices and clustering results can be downloaded in a single bash download script `run_download.sh`.

## User specifications for generating all files
The Cell Ranger `mkfastq` sample sheet must be generated and provided by the user before this script can run. In addition, the user must specify the location of a Cell Ranger `mkfastq` sample sheet template, that the script will modify with the appropriate settings. **Remember, sample names in the mkfastq sample sheet must follow the conventions described above.**

```commandline
reuse Anaconda3
use Google-Cloud-SDK
gcloud auth login dchafamo@broadinstitute.org
conda activate /broad/xavierlab_datadeposit/dchafamo/alto
wget http://github.com/dan-broad/scrnaseq_pipeline/archive/main.zip 
unzip main.zip && rm main.zip && cd ScPipelineKCO-main/src
nohup python sc_pipeline.py &> sc_out.txt &
```


