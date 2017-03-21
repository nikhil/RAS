#Usage:
#Rscript ~/RNASeqPipeline/RScripts/manual_classification.r label_list
library("monocle")
library("reshape")
args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=1)
{
	print("Usage: Rscript manual_classification.r label_list")
}
HSMM <- readRDS('post_quality_control_data.rds')
print(args[1])
pData(HSMM)$CellType <- unlist(strsplit(args[1],","))
print(plot_cell_trajectory(HSMM, color="CellType"))
ggsave("cell_classify_plot.png")
ggsave("cell_classify_plot.tiff", width = 7, height = 7,dpi=600)
saveRDS(HSMM,"classified_cells.rds")
pData(HSMM)$Size_Factor <- NULL
rownames(pData(HSMM)) <- NULL
pData(HSMM)$Total_mRNAs <- Matrix::colSums(exprs(HSMM))
write.table(pData(HSMM), 'manual_classification_table_after.txt', sep="\t",quote=FALSE)