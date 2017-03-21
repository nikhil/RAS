library("monocle")
library("reshape")
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
pData(HSMM)$Size_Factor <- NULL
rownames(pData(HSMM)) <- NULL
pData(HSMM)$Total_mRNAs <- Matrix::colSums(exprs(HSMM))
write.table(pData(HSMM), "mRNA_table.txt", sep="\t",quote=FALSE)