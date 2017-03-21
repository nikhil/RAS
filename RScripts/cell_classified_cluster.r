#Usage:
#Rscript cell_classified_cluster.r cluster_number
library("monocle")
library("reshape")
library('ggplot2')
args <- commandArgs(trailingOnly=TRUE)
if(length(args)==0)
{
	print("Usage: Rscript cell_classified_cluster.r cluster_number")
}
cluster_number <- args[1]
fpkm_matrix <- read.table('genes.fpkm_table', sep="\t", header = TRUE, row.names=1) # fpkm matrix
sample_sheet<- read.delim("samples.table", row.names=1) # sample sheet
gene_annotations<- read.delim("genes.attr_table", row.names=1) # gene annotations
fd<- new("AnnotatedDataFrame", data = gene_annotations)
pheno.data <- colnames(fpkm_matrix)
pheno.data <- unlist(lapply(pheno.data, function(x) strsplit(x, '_')[[1]][1]))
pheno.data.df <- data.frame(type=pheno.data)
rownames(pheno.data.df) <- colnames(fpkm_matrix)
row_names <- rownames(pheno.data.df)
pheno.data.df$name <- row_names
pheno.data.df$type <- NULL
pd <- new('AnnotatedDataFrame', data = pheno.data.df)
HSMM <- newCellDataSet(as.matrix(fpkm_matrix), phenoData = pd, featureData = fd)
HSMM <- clusterCells(HSMM, num_clusters=as.numeric(cluster_number))
HSMM_class <- readRDS("classified_cells.rds")
pData(HSMM)$CellType <- pData(HSMM_class)$CellType
print(plot_cell_trajectory(HSMM, color="CellType"))
ggsave("cell_classified_cluster_plot.png")
dev.off() 