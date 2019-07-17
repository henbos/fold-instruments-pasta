# fold-instruments-pasta

```
$ python fold-instruments-pasta.py --help
Usage:
  fold-instruments-pasta.py [inputFileName] [outputDirectory] [flameGraphFileName]

  inputFileName: Defaults to: profile-dump.pasta
  outputDirectory: Defaults to: out
  flameGraphFileName: Path to flamegraph.pl, see 
    https://github.com/brendangregg/FlameGraph. Defaults to
    ~/workspace/FlameGraph/flamegraph.pl

  The input file is obtained as follows:
  In Xcode Instruments, profile using the Time Profiler template.
  The resulting CPU Usage's Detail area will contain a root node
  for the entire process. Expand it -- IMPORTANT: but don't expand
  its children -- and you will have a list of all the threads.
  Select all children -- IMPORTANT: but don't select the root node.
  Having a selection of the roots of all threads, nothing less,
  nothing more, press Edit > Deep Copy. Paste the contents into a
  file; this is your input file to this program.

  The output file is a FlameGraph. This can be opened for example
  in Chrome.
```
