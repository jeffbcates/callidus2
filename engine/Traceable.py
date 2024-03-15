#trainers and analyzers are both traceable 
#tracing what happened during training is critical to figure out if something is going wrong with training

class Traceable:

    #are we even tracing?
    tracing = False

    #what is the trace file reference we are tracing to
    traceFile = None
    traceFileName = None

    #open the trace file for writing -> append content
    def openTrace(self, path, file):

        #we are tracing
        self.tracing = True

        #open the file if not already open
        self.traceFileName = "{}/{}".format(path, file)
        if self.traceFile == None: self.traceFile = open(self.traceFileName,"a+")

    #clear contents of file and write our header
    def traceHeader(self, *args):

        #close the file (currently opened)
        self.traceFile.close()

        #truncate the file
        self.traceFile = open(self.traceFileName,"w+")

        #write the header and close the file
        self.trace(*args)
        self.traceFile.close()

        #reopen the file in append mode again
        self.traceFile = open(self.traceFileName,"a+")


    #trace to our file
    def trace(self, *args):

        #quit if not tracing
        if self.tracing == False: return

        #step through each argument and build a pipe-delimited output string to trace
        output = ""
        for arg in args:

            #add this argument and a pipe
            output += str(arg) + "|"

        #write to the file, excluding the last pipe
        self.traceFile.write(output[:-1] + "\n")