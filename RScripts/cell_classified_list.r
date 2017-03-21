#Usage:
#Rscript cell_classified_list.r
library("monocle")
library("reshape")
HSMM <- readRDS("classified_cells.rds")
CellTypeList <- pData(HSMM)$CellType
#rownames(pData(CellTypeList)) <- NULL
write.table(CellTypeList, 'cell_type_list.txt', sep="\t",quote=FALSE,row.names=FALSE,col.names=FALSE)
write.table(exprs(HSMM), 'cell_exprs_list.txt', sep="\t",quote=FALSE)