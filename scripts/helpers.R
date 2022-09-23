#' Load raw seurat object for rna seq
#'
#' filtered_feature_bc_matrix.h5 should be under {raw.dir}/{sample}/
#'
LoadRawSeurat <- function(
  sample,
  raw.dir,
  processed.dir
) {
  if (file.exists(paste0(processed.dir, sample, ".raw.pbmcs.rds"))) {
    pbmc <- readRDS(paste0(processed.dir, sample, ".raw.pbmcs.rds"))
  } else {
    print(paste0("Reading from: ", raw.dir, sample, "/filtered_feature_bc_matrix.h5"))
    counts <- Read10X_h5(paste0(raw.dir, sample, "/filtered_feature_bc_matrix.h5"))
    pbmc <- CreateSeuratObject(counts = counts, assay = "RNA")
    pbmc[['Sample']] <- sample
    saveRDS(pbmc, paste0(processed.dir, sample, ".raw.pbmcs.rds"))
  }
  return(pbmc)
}

#' Downstream processing for rna seq data
#'
#' {sample}.raw.pbmcs.rds should be under {processed.dir}/
#' ref.path to the reference data, download from: (https://atlas.fredhutch.org/data/nygc/multimodal/pbmc_multimodal.h5seurat)
#'
ProcessMouseRNASeqSeurat <- function(
  sample,
  processed.dir,
  ref.path = "reference/pbmc_multimodal.h5seurat"
) {
  if (file.exists(paste0(processed.dir, sample, ".processed.pbmc.rds"))) {
    pbmc <- readRDS(paste0(processed.dir, sample, ".processed.pbmc.rds"))
  } else {
    pbmc <- readRDS(paste0(processed.dir, sample, ".raw.pbmcs.rds"))

    # QC filtering
    pbmc[["percent.mt"]] <- PercentageFeatureSet(pbmc, pattern = "^mt-")
    pbmc <- subset(pbmc, subset = nCount_RNA > 400 &
      nFeature_RNA > 200 &
      percent.mt < 20)
    pbmc.raw <- pbmc

    # Dim Reduction
    pbmc <- SCTransform(pbmc, verbose = FALSE)
    pbmc <- RunPCA(pbmc, npcs = 30, verbose = FALSE)
    pbmc <- RunUMAP(pbmc, reduction = "pca", dims = 1:30, verbose = FALSE)
    pbmc <- FindNeighbors(pbmc, reduction = "pca", dims = 1:30, verbose = FALSE)
    pbmc <- FindClusters(pbmc, resolution = 0.1, verbose = FALSE)
    pbmc <- FindVariableFeatures(pbmc, selection.method = "vst", nfeatures = 2000)

    # Celltype annotation
    pbmc.hum <- pbmc.raw
    mouse.genes <- pbmc.hum@assays$RNA@counts@Dimnames[[1]]

    human <- useEnsembl(biomart = "ensembl", dataset = "hsapiens_gene_ensembl", version = "98")
    mouse <- useEnsembl(biomart = "ensembl", dataset = "mmusculus_gene_ensembl", version = "98")

    genesV2 = getLDS(
      attributes = c("mgi_symbol"),
      filters = "mgi_symbol",
      values = mouse.genes,
      mart = mouse,
      attributesL = c("hgnc_symbol"),
      martL = human,
      uniqueRows = TRUE
    )

    genesV2.unique <- genesV2 %>% distinct(MGI.symbol, .keep_all = TRUE)
    row.names(genesV2.unique) <- genesV2.unique$MGI.symbol
    human.genes <- genesV2.unique[mouse.genes, 2]
    head(human.genes)

    RenameGenesSeurat <- function(obj, newnames) {
      RNA <- obj@assays$RNA

      if (nrow(RNA) == length(newnames)) {
        if (length(RNA@counts)) RNA@counts@Dimnames[[1]] <- newnames
        if (length(RNA@data)) RNA@data@Dimnames[[1]] <- newnames
        if (length(RNA@scale.data)) RNA@scale.data@Dimnames[[1]] <- newnames
      } else { "Unequal gene sets: nrow(RNA) != nrow(newnames)" }
      obj@assays$RNA <- RNA
      return(obj)
    }

    subset.matrix <- pbmc.hum@assays$RNA@data[!is.na(rownames(pbmc.hum)),]
    pbmc.hum <- CreateSeuratObject(subset.matrix)
    pbmc.hum@assays$RNA

    pbmc.hum <- SCTransform(pbmc.hum, verbose = FALSE)
    pbmc.hum <- RunPCA(pbmc.hum, npcs = 30, verbose = FALSE)
    pbmc.hum <- RunUMAP(pbmc.hum, reduction = "pca", dims = 1:30, verbose = FALSE)
    pbmc.hum <- FindNeighbors(pbmc.hum, reduction = "pca", dims = 1:30, verbose = FALSE)

    reference <- LoadH5Seurat(ref.path)
    DefaultAssay(pbmc.hum) <- "SCT"

    transfer_anchors <- FindTransferAnchors(
      reference = reference,
      query = pbmc.hum,
      normalization.method = "SCT",
      reference.reduction = "spca",
      recompute.residuals = FALSE,
      dims = 1:50
    )

    pbmc.hum <- MapQuery(
      anchorset = transfer_anchors,
      query = pbmc.hum,
      reference = reference,
      refdata = list(
        celltype.l1 = "celltype.l1",
        celltype.l2 = "celltype.l2",
        predicted_ADT = "ADT"
      ),
      reference.reduction = "spca",
      reduction.model = "wnn.umap"
    )

    # add labels to orignal pbmc
    pbmc[["predicted.celltype.l1"]] <- pbmc.hum[["predicted.celltype.l1"]]
    pbmc[["predicted.celltype.l2"]] <- pbmc.hum[["predicted.celltype.l2"]]

    saveRDS(pbmc, paste0(processed.dir, sample, ".processed.pbmc.rds"))
  }
  return(pbmc)
}