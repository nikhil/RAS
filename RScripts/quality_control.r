#Usage:
#Rscript quality_control.r lower_bound upper_bound min_gene_expression min_cells
library("monocle")
library("reshape")
args <- commandArgs(trailingOnly=TRUE)
lower_bound <- as.numeric(args[1])
upper_bound <- as.numeric(args[2])
min_gene_expression <- as.numeric(args[3])
min_cells <- as.numeric(args[4]) 

if(length(args)!=4)
{
	print("Usage: Rscript quality_control.r lower_bound upper_bound min_gene_expression min_cells")
}
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
pData(HSMM)$Total_mRNAs <- Matrix::colSums(exprs(HSMM))
HSMM <- detectGenes(HSMM, min_expr = min_gene_expression)
HSMM <- HSMM[,pData(HSMM)$Total_mRNAs > lower_bound & pData(HSMM)$Total_mRNAs < upper_bound]
is_significant_gene <- apply(exprs(HSMM),1,function(x) length(x[x>min_gene_expression])>min_cells)
gene_names <- names(which(is_significant_gene == TRUE))
write.table(length(gene_names),"num_genes.txt", sep="\t",quote=FALSE)
fData(HSMM) <- fData(HSMM)[gene_names,]
new_fpkm <- fpkm_matrix[gene_names,]
fd<- new("AnnotatedDataFrame", data = fData(HSMM))
pd<- new("AnnotatedDataFrame", data = pData(HSMM))
#print(names(is_significant_gene)[1])
#print(length(names(is_significant_gene)))

#significant_genes <- row.names(subset(exprs(HSMM)), length(exprs(HSMM)[exprs(HSMM) > 1]))

##expressed_genes <- row.names(subset(fData(HSMM), num_cells_expressed >= 3))
##fData(HSMM) <- fData(HSMM)[expressed_genes,]

#fData(HSMM) <- fData(HSMM)[,expressed_genes]
#HSMM <- newCellDataSet(as.matrix(fpkm_matrix), phenoData = pd, featureData = fData(HSMM))

##fd<- new("AnnotatedDataFrame", data = fData(HSMM))
##pd<- new("AnnotatedDataFrame", data = pData(HSMM))
##new_fpkm <- fpkm_matrix[expressed_genes,]
HSMM <- newCellDataSet(as.matrix(new_fpkm), phenoData = pd, featureData = fd)
##print(head(exprs(HSMM)))
##print(head(fData(HSMM)))
##print(nrow(fData(HSMM)))
saveRDS(HSMM,'post_quality_control_data.rds')
pData(HSMM)$Size_Factor <- NULL
rownames(pData(HSMM)) <- NULL
pData(HSMM)$Total_mRNAs <- Matrix::colSums(exprs(HSMM))
write.table(pData(HSMM), "post_quality_control.txt", sep="\t",quote=FALSE)