import os
import shutil
import subprocess
import sys

class StackTraceNode:
  def __init__(self, columnSelfWeight, columnSymbolName):
    self.parent_ = None
    self.children_ = []
    self.selfWeightMs_ =\
        StackTraceNode.parseColumnSelfWeight(columnSelfWeight)
    (self.depth_, self.symbolName_) =\
        StackTraceNode.parseColumnSymbolName(columnSymbolName)

  def parent(self):
    return self.parent_

  def setParent(self, parent):
    if parent != None and not isinstance(parent, StackTraceNode):
      print("ERROR @ StackTraceNode: parent is not a StackTraceNode")
      sys.exit()
    self.parent_ = parent

  def children(self):
    return self.children_

  def addChild(self, child):
    if not isinstance(child, StackTraceNode):
      print("ERROR @ addChild: child is not a StackTraceNode")
      sys.exit()
    self.children_.append(child)

  def selfWeightMs(self):
    return self.selfWeightMs_

  def depth(self):
    return self.depth_
 
  def symbolName(self):
    return self.symbolName_

  # Single node string representation (parents and children are not included).
  # Has depth() number of leading whitespaces, the symbol names and the
  # self-weight and depth.
  def __str__(self):
    spaces = ""
    for i in range(0, self.depth_):
      spaces = "{} ".format(spaces)
    return "{}{} [{} ms, depth {}]".format(spaces, self.symbolName_,\
                                           self.selfWeightMs_, self.depth_)
  
  # Detailed representation of the entire tree. This includes the entire stack
  # trace, marking this node's line with a leading "=>".
  def __repr__(self):
    ret = ""
    for i in range(0, self.depth_):
      if i == 0:
        ret = "  {}".format(str(self.getParentNodeAtDepth(i)))
      else:
        ret = "{}\n  {}".format(ret, str(self.getParentNodeAtDepth(i)))
    if self.depth_ == 0:
      ret = "=>{}".format(str(self))
    else:
      ret = "{}\n=>{}".format(ret, str(self))
    for child in self.children_:
      ret = "{}\n{}".format(ret, child.__selfAndChildrenToString(ret))
    return ret

  def getParentNodeAtDepth(self, depth):
    if depth > self.depth_:
      print("ERROR @ getParentNodeAtDepth: depth > self.depth_")
      sys.exit()
    if depth < self.depth_:
      return self.parent_.getParentNodeAtDepth(depth)
    return self
  
  # Helper method for __repr__. Each node is listed with 2 leading whitespaces.
  def __selfAndChildrenToString(self, ret):
    ret = "  {}".format(str(self))
    for child in self.children_:
      ret = "{}\n  {}".format(ret, child.__selfAndChildrenToString(ret))
    return ret

  @staticmethod
  def parseColumnSelfWeight(columnSelfWeight):
    [weightStr, unit] = columnSelfWeight.split(" ")
    weight = None
    try:
      weight = float(weightStr)
    except ValueError:
      print("ERROR @ parseColumnSelfWeight: Failed to parse as float: {}"\
            .format(weightStr))
      sys.exit()
    if unit == "s":
      weight *= 1000  # s -> ms
    elif unit != "ms":
      print("ERROR @ parseColumnSelfWeight: Expected s or ms, got {}"\
            .format(unit))
      sys.exit()
    return weight
  
  @staticmethod
  def parseColumnSymbolName(columnSymbolName):
    depth = 0
    while depth < len(columnSymbolName) and columnSymbolName[depth] == " ":
      depth += 1
    symbolName = columnSymbolName[depth:]
    if len(symbolName) <= 0:
      print("ERROR @ parseColumnSymbolName: Empty symbol name")
      sys.exit()
    return (depth, symbolName)

# Input: StackTraceNode
# Output: The .folded format. Each line has this format:
#   Semi;Colon;Separated;Stack;Trace SelfWeight
# Where SelfWeight = 0 lines are excluded.
# Multiple StackTraceNodes (such as multiple thread root nodes) can be outputted
# to the same file sequentially.
def FoldStackTrace(node, parents, file):
  if node.selfWeightMs() != 0:
    line = ""
    for parent in parents:
      if line == "":
        line = parent.symbolName()
      else:
        line = "{};{}".format(line, parent.symbolName())
    if line == "":
      line = node.symbolName()
    else:
      line = "{};{}".format(line, node.symbolName())
    line = "{} {}".format(line, int(node.selfWeightMs()))
    file.write("{}\n".format(line))
  for child in node.children():
    FoldStackTrace(child, parents + [node], file)

def WriteFoldedFileFromStackTraceNodes(fileName, threadNodes):
  with open(fileName, "w") as outputFile:
    for threadNode in threadNodes:
      FoldStackTrace(threadNode, [], outputFile)
    print("  * Wrote {} bytes to {}.".format(outputFile.tell(), fileName))

def ExecuteFlameGraph(\
    flameGraphFileName, inputFoldedFileName, outputSvgFileName):
  command = "{} \"{}\" > \"{}\"".format(\
            flameGraphFileName, inputFoldedFileName, outputSvgFileName)
  try:
    subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
  except subprocess.CalledProcessError as e:
    print("    Failed to execute:\n  {}\nCommand output:\n  {}".format(\
          command, e.output))
    sys.exit()
  outputSize = os.path.getsize(outputSvgFileName)
  print("    FlameGraph: Wrote {} bytes to {}.".format(\
        outputSize, outputSvgFileName))

def WriteFlameGraphFromThreadNodes(\
    flameGraphFileName, foldedFileName, svgFileName, threadNodes):
  WriteFoldedFileFromStackTraceNodes(foldedFileName, threadNodes)
  ExecuteFlameGraph(flameGraphFileName, foldedFileName, svgFileName)
  os.remove(foldedFileName)
  print("    Deleted temporary file {}.".format(foldedFileName))

def main():
  # Input to the program.
  inputFileName = "profile-dump.pasta"
  if len(sys.argv) >= 2:
    inputFileName = sys.argv[1]
  outputDirectory = "out"
  if len(sys.argv) >= 3:
    outputDirectory = sys.argv[2]
  flameGraphFileName = "~/workspace/FlameGraph/flamegraph.pl"
  if len(sys.argv) >= 4:
    flameGraphFileName = sys.argv[3]

  # Display help menu.
  if inputFileName == "-h" or inputFileName == '--help' or\
     inputFileName == 'help':
    print("Usage:\n  {} [inputFileName] [outputDirectory] [flameGraphFileName]"\
          .format(sys.argv[0]))
    print("")
    print("  inputFileName: Defaults to: profile-dump.pasta")
    print("  outputDirectory: Defaults to: out")
    print("  flameGraphFileName: Path to flamegraph.pl, see ")
    print("    https://github.com/brendangregg/FlameGraph. Defaults to")
    print("    ~/workspace/FlameGraph/flamegraph.pl")
    print("")
    print("  The input file is obtained as follows:")
    print("  In Xcode Instruments, profile using the Time Profiler template.")
    print("  The resulting CPU Usage's Detail area will contain a root node")
    print("  for the entire process. Expand it -- IMPORTANT: but don't expand")
    print("  its children -- and you will have a list of all the threads.")
    print("  Select all children -- IMPORTANT: but don't select the root node.")
    print("  Having a selection of the roots of all threads, nothing less,")
    print("  nothing more, press Edit > Deep Copy. Paste the contents into a")
    print("  file; this is your input file to this program.")
    print("")
    print("  The output file is a FlameGraph. This can be opened for example")
    print("  in Chrome.")
    print("")
    return

  # Create output folder, deleting it first if it already exists.
  if outputDirectory != ".":
    if os.path.isdir(outputDirectory):
      print("Deleting existing output directory: {}".format(outputDirectory))
      shutil.rmtree(outputDirectory)
    print("Creating output directory: {}".format(outputDirectory))
    os.mkdir(outputDirectory)
    print("")

  # Parse input file.
  print("Parsing {}...".format(inputFileName))
  with open(inputFileName) as inputFile:
    lineCount = 0
    threadCount = 0
    currentThreadStartLine = None
    previousNode = None
    threadNodes = []
    for line in inputFile:
      lineCount += 1
      # Remove newline character
      line = line[:-1]
      # Ignore emtpy lines. These are used to separate threads, but we only have
      # to look at the the start of a new thread (see below).
      if line == "":
        continue
      if line == "Weight\tSelf Weight\t\tSymbol Name":
        threadCount += 1
        currentThreadStartLine = lineCount
        previousNode = None
        # print("Line #{} marks a new thread".format(lineCount))
        continue
      columns = line.split('\t')
      # This should be a common line. Examples:
      #
      # columns[0] is Weight:
      #   "4.77 s  100.0%"
      #   "827.00 ms   17.3%"
      #   This is the weight in seconds or milliseconds, then three spaces, then
      #   the weight as a percentage. This is the Self Weight plus the
      #   childrens' Weight.
      #
      # columns[1] is Self Weight:
      #   "0 s"
      #   This is the time spent inside this function, excluding time spend in
      #   children.
      #
      # columns[2] is Library Category Item:
      #   " "
      #   This is an icon inside Instruments, this gets copied like a space.
      #   We ignore it.
      #
      # columns[3] is Symbol Name:
      #   " base::internal::WorkerThread::RunPooledWorker  0x6574f4"
      #   "     base::(anonymous namespace)::ThreadFunc(void*)"
      #   The depth of the callstack is the number of leading spaces.
      #
      # All measurements are in millisecond precision, you will never see a
      # fraction of a millisecond.
      #
      # For the ".folded" output we only care about the leaf nodes' Self Weight,
      # where we can count 1 ms as 1 sample.
      #
      if len(columns) != 4:
        print("ERROR: Expected 4 columns, got {}".format(len(columns)))
        sys.exit()
      currentNode = StackTraceNode(columns[1], columns[3])
      if previousNode == None:
        threadNodes.append(currentNode)
      else:
        currentNode.setParent(\
            previousNode.getParentNodeAtDepth(currentNode.depth() - 1))
        currentNode.parent().addChild(currentNode)
      previousNode = currentNode
  print("  {} lines were parsed. {} threads (root nodes) found.".format(\
        lineCount, threadCount))
  if threadCount != len(threadNodes):
    print("ERROR: Thread count != thread nodes")
    sys.exit()

  # Write output files.
  print("")
  print("Writing output file containing all threads...")
  WriteFlameGraphFromThreadNodes(\
      flameGraphFileName,\
      "{}/FULL-OUTPUT.folded".format(outputDirectory),\
      "{}/FULL-OUTPUT.svg".format(outputDirectory),\
      threadNodes)
  print("")
  print("Writing per-thread output files...")
  for threadNode in threadNodes:
    WriteFlameGraphFromThreadNodes(\
        flameGraphFileName,\
        "{}/{}.folded".format(outputDirectory, threadNode.symbolName()),\
        "{}/{}.svg".format(outputDirectory, threadNode.symbolName()),\
        [threadNode])

if __name__ == "__main__":
  main()
