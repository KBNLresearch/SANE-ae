## Contents of this repo

This repo contains a script that is meant to be used within the SANE environment for extracting accessibility info from e-books. It wraps around the *rwp* tool that is part of the [Readium Go Toolkit](https://github.com/readium/go-toolkit). A Linux binary of *rwp* is included in this repo. Supported formats are EPUB and PDF.

## ae.py

Get accessibility info from all Ebooks in a directory tree using Readium Go's Rwp tool. Output is wrapped in a TAR file, with file info in separate JSON as Rwp doesn't report this directly.

## Command-line syntax

```
python3 ae.py pathIn pathOut
```

With:

- pathIn: input directory
- pathOut: output directory

Example:

```
python3 ae.py /home/johan/kb/epub-accessibility/eregalerij/ .
```

## Output

- analyzer.tar: TAR archive with output
- analyzer.log: log file

The output TAR contains one directory for each processed file. The name of each directory is the file's MD5 hash. If the input directory tree contains multiple instances of the same file (as per its hash), only the first occurrence is included in the output TAR. Each directory contains the following files:

- fileinfo.json: JSON file with name and full path of each Ebook file
- rwp.json: JSON file with output of rwp tool
