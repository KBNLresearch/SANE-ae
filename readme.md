## Contents of this repo

This repo contains a script that is meant to be used within the SANE environment for extracting accessibility info from e-books. It wraps around the *rwp* tool that is part of the [Readium Go Toolkit](https://github.com/readium/go-toolkit). A Linux binary of *rwp* is included in this repo.

Currently only EPUB files (identified by the ".epub" file extension) are supported! Although the *rwp* tool also supports PDF, preliminary tests resulted in various problems, so PDF files are ignored in this version.

## ae.py

Get accessibility info from all Ebooks in a directory tree using Readium Go's Rwp tool. Output is wrapped in a TAR file, with file info in separate JSON as Rwp doesn't report this directly.

## Input directory structure

The script assumes a flat directory structure, where the input dir contains 1 level of child directories, that each contain one Ebook. Here's an example:

```
./dirIn
├── IP1523369858048
│   └── 20161227153031_9789400403178.epub
├── IP1564040668928
│   └── 20190627233027_9789029582179.epub
└── IP1700049667584
    └── 20221207163015_9789044934458.epub
```

## Command-line syntax

```
python3 ae.py pathIn pathOut --prefixOut PREFIXOUT
```

With:

- pathIn: input directory
- pathOut: output directory
- PREFIXOUT: optional output prefix (default: "sane-ae")

Example:

```
python3 ae.py /home/johan/kb/epub-accessibility/eregalerij/ .
```

## Output

- sane-ae.tar: TAR archive with output
- sane-ae.log: log file

The output TAR contains one directory for each processed file. The name of each directory corresponds to the name of the direct parent directory of the imput file. Each directory contains the following files:

- fileinfo.json: JSON file with, for each Ebook file, its name, full file path, the file format, the full rwp command line and the rwp exit status 
- rwp.json: JSON file with output of thev rwp tool
