#Usage:
#Rscript cell_classified_pseudotime_genes.r FDR_value num_clusters
library("monocle")
library("reshape")
library('ggplot2')
args <- commandArgs(trailingOnly=TRUE)
if(length(args)==0)
{
	print("Usage: Rscript cell_classified_pseudotime_genes.r FDR_value num_clusters")
}
num_genes <- args[1]
num_clusters <- args[2]
#HSMM <- readRDS("classified_cells.rds")
HSMM <- readRDS("reduded_dimension.rds")
#HSMM_myo <- reduceDimension(HSMM, max_components=2)
#HSMM_myo <- orderCells(HSMM_myo, reverse=FALSE)

#diff_test_res <- differentialGeneTest(HSMM_myo, fullModelFormulaStr="~CellType")
#sig_genes <- subset(diff_test_res, qval < as.numeric(FDR_value))
#HSMM <- reduceDimension(HSMM, max_components=as.numeric(dimension_number))
#HSMM <- orderCells(HSMM, reverse=FALSE)
#print(plot_cell_trajectory(HSMM, color_by="CellType"))
#HSMM <- reduceDimension(HSMM, max_components=2)
#saveRDS(HSMM,'reduded_dimension.rds')
#print(head(pData(HSMM)))
#rpc_matrix <- relative2abs(HSMM, cores = detectCores())
#pd <- new("AnnotatedDataFrame", data = pData(HSMM))
#fd <- new("AnnotatedDataFrame", data = fData(HSMM))
#HSMM <- newCellDataSet(as(as.matrix(rpc_matrix), "sparseMatrix"),phenoData = pd,featureData = fd,lowerDetectionLimit=1,expressionFamily=negbinomial.size())
#HSMM <- estimateSizeFactors(HSMM)
#HSMM <- estimateDispersions(HSMM)
#HSMM <- reduceDimension(HSMM, max_components=2)
#HSMM <- orderCells(HSMM, reverse=FALSE)
#saveRDS(HSMM,'reduded_dimension.rds')


#print(head(pData(HSMM)))
#pData(HSMM)$Pseudotime = pData(HSMM_reduced)$Pseudotime
#print("second part")
#BEAM_res <- BEAM(HSMM, branch_point=1, cores = detectCores())
#BEAM_res <- BEAM_res[order(BEAM_res$qval),]
#BEAM_res <- BEAM_res[,c("gene_short_name", "pval", "qval")]
#print(plot_genes_branched_heatmap(HSMM[row.names(subset(BEAM_res, qval < as.numeric(FDR_value))),],branch_point = 1,num_clusters = as.numeric(num_clusters),cores = detectCores(),use_gene_short_name = T,show_rownames = T))
#print(plot_pseudotime_heatmap(HSMM_myo[sig_genes,],num_clusters = as.numeric(num_clusters),show_rownames = T))
HSMM <- orderCells(HSMM, reverse=FALSE)

#print("0")
library(pheatmap)
diff_test_res <- differentialGeneTest(HSMM,fullModelFormulaStr="~CellType",cores = detectCores())
new_diff <- diff_test_res[order(diff_test_res$qval),]
#new_diff[1:100,]
newHSMM <- HSMM[rownames(new_diff[1:100,]),]
expression_matrix <- exprs(newHSMM)
colnames(expression_matrix) <- pData(newHSMM)$CellType
sorted_matrix <- expression_matrix[,order(colnames(expression_matrix))]
Cell_Type <- colnames(sorted_matrix)
colnames(sorted_matrix) <- 1:length(colnames(sorted_matrix))
annotation_data <- data.frame(Cell_Type)
rownames(annotation_data) <-colnames(sorted_matrix)
log_matrix <- log(sorted_matrix)
log_matrix[log_matrix==-Inf] <- 0
png('heatmap5.png',width = 10, height = 10, units= 'in',res=600)
pheatmap(log(sorted_matrix), annotation=annotation_data,cluster_cols = FALSE,cluster_rows = FALSE,show_colnames = FALSE,scale='row')



png('cell_classified_heatmap_plot.png', width = 10, height = ceiling(as.numeric(num_genes)/10), units= 'in',res=600)

#saveRDS(diff_test_res,'diff_test_res.rds')
#print('1')
#print(diff_test_res$qval)
#sig_gene_names <- row.names(subset(diff_test_res, qval < .5))
#print(sig_gene_names)
#print("2")
#print(plot_pseudotime_heatmap(HSMM[sig_gene_names,],num_clusters = 2,cores = detectCores(),show_rownames = T))

ggsave("cell_classified_heatmap_plot.png")
ggsave("cell_classified_heatmap_plot.tiff", width = 7, height = 7,dpi=600)
dev.off() 