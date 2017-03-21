library(cummeRbund)
cuff <- readCufflinks()
Samples <-samples(genes(cuff))
Sample_data <- data.frame(Samples)
write.table(Sample_data, 'sample_list.txt', sep="\t",quote=FALSE)

