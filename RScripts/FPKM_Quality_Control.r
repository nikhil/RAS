library(cummeRbund)
args <- commandArgs(trailingOnly=TRUE)
error_file <- file(args[1], open="wt")
sink(error_file, type="message")
cuff <- readCufflinks()
genes.scv<-fpkmSCVPlot(genes(cuff))
png(args[2],width = 10, height = 10, units= 'in',res=600)
print(genes.scv)
dev.off()