#Usage:
#Rscript cell_classified_differential.r gene_list gene_class
library("monocle")
library("reshape")
library("ggplot2")
library("pheatmap")
args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=2)
{
	print("Usage: Rscript cell_classified_differential.r gene_list gene_class")
}
HSMM <- readRDS("classified_cells.rds")
gene_list <-  unlist(strsplit(args[1],","))
gene_class <- unlist(strsplit(args[2],","))
saveRDS(gene_list,'gene_list.rds')
saveRDS(gene_class,'gene_class.rds')
newHSMM <- HSMM[gene_list,]
expression_matrix <- exprs(newHSMM)
colnames(expression_matrix) <- pData(newHSMM)$CellType
sorted_matrix <- expression_matrix[order(gene_class),order(colnames(expression_matrix))]
Cell_Type <- colnames(sorted_matrix)
colnames(sorted_matrix) <- 1:length(colnames(sorted_matrix))
annotation_col_data <- data.frame(Cell_Type)
annotation_row_data <- data.frame(gene_class[order(gene_class)])
rownames(annotation_row_data) <- rownames(sorted_matrix)
names(annotation_row_data) <- "Gene Class"
names(annotation_col_data) <- "Cell Type"
log_matrix <- log(sorted_matrix+1)
png('cell_classified_heatmap.png',width = ceiling(length(rownames(annotation_col_data))/10), height = ceiling(length(rownames(annotation_row_data))/8), units= 'in',res=600)
pheatmap(log_matrix, annotation_col=annotation_col_data,annotation_row=annotation_row_data,cluster_cols = FALSE,cluster_rows = FALSE,show_colnames = FALSE)
dev.off()