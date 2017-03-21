#Usage:
#Rscript ~/RNASeqPipeline/RScripts/trim_data.r range
library("monocle")
library("reshape")
args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=1)
{
	print("Usage: Rscript trim_data.r range")
}
HSMM <- readRDS('post_quality_control_data.rds')
#print(HSMM)
HSMM <- HSMM[, strtoi(unlist(strsplit(args[1],",")))]
saveRDS(HSMM,'post_quality_control_data.rds')
pData(HSMM)$Size_Factor <- NULL
rownames(pData(HSMM)) <- NULL
pData(HSMM)$Total_mRNAs <- Matrix::colSums(exprs(HSMM))
write.table(pData(HSMM), 'trim_table_after.txt', sep="\t",quote=FALSE)