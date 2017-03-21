library(cummeRbund)
args <- commandArgs(trailingOnly=TRUE)
error_file <- file(args[1], open="wt")
sink(error_file, type="message")
cuff <- readCufflinks()
my_gene_id<-args[3]
my_gene <- getGene(cuff,my_gene_id)
bar_plot <- expressionBarplot(my_gene)
png(args[2],width = 10, height = 10, units= 'in',res=600)
print(bar_plot)
dev.off()

