#! /usr/bin/env python3
"""
Get accessibility info from all EPUB and PDF files in a directory tree using 
Readium Go's Rwp tool.
Output is wrapped in a TAR file, with file info in separate JSON as
Rwp doesn't report this directly.

Code assumes a flat directory structure, where the input dir contains 1 level
of child dirs that each contain one Ebook.

"""

import sys
import os
import shutil
import argparse
import logging
import tarfile
import json
import subprocess as sub

# Create argument parser
PARSER = argparse.ArgumentParser(
                                    description="Simple wrapper for Readium Go Rwp")

def parseCommandLine():
    """Parse command line arguments."""

    PARSER.add_argument('--dirIn','-i',
                        action="store",
                        type=str,
                        help="input directory",
                        required=True)
    PARSER.add_argument('--dirOut', '-o',
                        action="store",
                        type=str,
                        help="output directory",
                        required=True)
    PARSER.add_argument('--dirTemp', '-t',
                        action="store",
                        type=str,
                        help="temporary directory",
                        required=True)
    PARSER.add_argument('--prefixOut', '-p',
                        action="store",
                        default="sane-ae",
                        help="output prefix")
    args = PARSER.parse_args()

    return args


def printWarning(msg):
    """Print warning to stderr."""
    msgString = "WARNING: " + msg + "\n"
    sys.stderr.write(msgString)


def errorExit(msg):
    """Print error to stderr and exit."""
    msgString = "ERROR: " + msg + "\n"
    sys.stderr.write(msgString)
    sys.exit(1)


def writeInfo(fileIn, rwpCommand, rwpStatus, fileOut):
    """Write file info to Json"""

    success = True

    # Dictionary with fields we want to write
    infoDict = {}
    infoDict["fileName"] = os.path.basename(fileIn)
    infoDict["filePath"] = fileIn

    fileName, fileExtension = os.path.splitext(fileIn)
    if fileExtension == ".epub":
        infoDict["format"] = "epub"
    elif fileExtension == ".pdf":
        infoDict["format"] = "pdf"

    infoDict["rwpCommand"] = rwpCommand
    infoDict["rwpStatus"] = rwpStatus

    # Save contents as JSON file
    try:
        with open(fileOut, "w", encoding="utf-8") as fOut:
            json.dump(infoDict, fOut, sort_keys=True, indent=4)

    except Exception:
        success = False

    return success


def runRwp(rwp, fileIn, fileOut):
    """Run Rwp on one file"""

    # This flag defines how subprocesses are executed 
    shellFlag = False

    # Arguments
    args = [rwp]
    args.append('manifest')
    args.append('--infer-a11y')
    args.append('split')
    args.append('--infer-page-count')
    args.append('-i')
    args.append(fileIn)

    # Command line as string (used for logging purposes only)
    cmdStr = " ".join(args)

    try:
        p = sub.Popen(args,
                      stdout=sub.PIPE,
                      stderr=sub.PIPE,
                      shell=shellFlag,
                      universal_newlines=True)
        stdout, stderr = p.communicate()
        exitStatus = p.poll()

        if exitStatus not in [0]:
            printWarning("rwp exit status was " + str(exitStatus))

        with open(fileOut, "w", encoding="utf-8") as fOut:
            fOut.write(stdout)

    except Exception:
        # I don't even want to to start thinking how one might end up here ...
        exitStatus = -99
        printWarning("Exception while running rwp")

    # All results to dictionary
    dictOut = {}
    dictOut["status"] = exitStatus
    dictOut["cmdStr"] = cmdStr

    return dictOut


def main():
    """Main command line application."""
    # Path to this script
    scriptPath = os.path.dirname(os.path.realpath(__file__))

    # Full path to rwp
    rwp = os.path.join(scriptPath, "rwp", "rwp")

    # Check that rwp is available
    if shutil.which(rwp) is None:
        msg = "Rwp is not installed"
        errorExit(msg)

    # Get input from command line
    args = parseCommandLine()

    # Input path
    pathIn = os.path.abspath(args.dirIn)
    # Output path
    pathOut = os.path.abspath(args.dirOut)
    # Temp path
    pathTemp = os.path.abspath(args.dirTemp)

    # Output prefix
    prefixOut = args.prefixOut

    # Output files
    tarOut = os.path.join(pathOut, ("{}.tar").format(prefixOut))
    logOut = os.path.join(pathOut, ("{}.log").format(prefixOut))

    # Set up logging config (stderr + file)
    logging.basicConfig(format='%(levelname)s: %(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        handlers=[logging.FileHandler(logOut),
                                  logging.StreamHandler()],
                        level=logging.DEBUG)

    logging.info('### SESSION START')

    # Temporary output files file info and Rwp
    fileInfoTemp = os.path.join(pathTemp, 'fileinfotemp.json')
    rwpOutTemp = os.path.join(pathTemp, 'rwptemp.json')

    # List with Ebooks that are to be processed
    ebooksIn = []

    # List with Ebook file extensions
    # For now exclude PDF because rwp hangs on most PDF files!
    # fExtensions = [".epub", ".pdf"]
    fExtensions = [".epub"]

    # Recursively scan pathIn for Ebook files
    for path, dirs, files in os.walk(pathIn):
        for name in (files):
            fileName, fileExtension = os.path.splitext(name)
            if fileExtension in fExtensions:
                ebooksIn.append(os.path.join(path, name))

    noEbooks = len(ebooksIn)

    # Names for output files that are written to TAR
    nameInfo = "fileinfo.json"
    nameOutRwp = "rwp.json"

    # List with all directory paths in TAR
    tarDirs = []

    try:
        with tarfile.open(tarOut, "r") as tf:
            # List of all current paths inside TAR
            tarFilePaths = tf.getnames()
            for fPath in tarFilePaths:
                tPath, tName = os.path.split(fPath)
                tarDirs.append(tPath)
    except IOError:
        tarDirs = []

    # Remove duplicates
    tarDirs = list(dict.fromkeys(tarDirs))

    counter = 1

    for ebook in ebooksIn:

        # Construct TAR output paths
        # TODO: this currently uses the name of the direct parent dir of each
        # Ebook. This works fine for flat input directory structures, but for
        # nested structures duplicate names are possible, which could 
        # result in unexpected behaviour!
        #
        # Also, if an input directory contains more than one Ebook, only the
        # first one will be processed, and any subsequent files are skipped.
        fPath, fName = os.path.split(ebook)
        dirIn = os.path.basename(fPath)
        logging.info('*****')
        logging.info(('file {}/{}').format(str(counter), str(noEbooks)))
        logging.info(fName)
        tarDir = os.path.join(dirIn)

        tarOutInfo = os.path.join(tarDir, nameInfo)
        tarOutRwp = os.path.join(tarDir, nameOutRwp)

        # Open TAR archive
        with tarfile.open(tarOut, "a") as tf:
            rwpCommand = ""
            rwpStatus = ""
            # Only process current file if path doesn't already exist
            # This also means duplicates of already processed files will
            # be skipped!
            if tarDir not in tarDirs:
                # Run Rwp
                rwpResult = runRwp(rwp, ebook, rwpOutTemp)
                if rwpResult["status"] in [0, 1]:
                    tf.add(rwpOutTemp, arcname=tarOutRwp)
                    tarDirs.append(tarDir)
                    rwpCommand = rwpResult["cmdStr"]
                    rwpStatus = rwpResult["status"]
                else:
                    logging.warning('failed running Rwp')
                # Remove temp file
                os.remove(rwpOutTemp)
                # Write file info
                infoSuccess = writeInfo(ebook, rwpCommand, rwpStatus, fileInfoTemp)
                if infoSuccess:
                    tf.add(fileInfoTemp, arcname=tarOutInfo)
                else:
                    logging.warning('failed writing file info')
                # Remove temp file
                os.remove(fileInfoTemp)
                msg = ('rwp command: {}').format(rwpCommand)
                logging.info(msg)
                msg = ('rwp exit code: {}').format(str(rwpStatus))
                logging.info(msg)
            else:
                logging.warning('TAR path already exists, skipping')

        counter += 1


if __name__ == "__main__":
    main()
