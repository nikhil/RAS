library("monocle")
library("reshape")
args <- commandArgs(trailingOnly=TRUE)
HSMM <- readRDS('post_quality_control_data.rds')
pData(HSMM)$Size_Factor <- NULL
rownames(pData(HSMM)) <- NULL
pData(HSMM)$Total_mRNAs <- Matrix::colSums(exprs(HSMM))
write.table(pData(HSMM), "before_decision_tree_pData_table.txt", sep="\t",quote=FALSE)
write.table(exprs(HSMM), "before_decision_tree_exprs_table.txt", sep="\t",quote=FALSE)