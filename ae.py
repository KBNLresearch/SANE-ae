#! /usr/bin/env python3
"""
Get accessibility info from all EPUB and PDF files in a directory tree using 
Readium Go's Rwp tool.
Output is wrapped in a TAR file, with file info in separate JSON as
Rwp doesn't report this directly.
"""

import sys
import os
import shutil
import argparse
import logging
import tarfile
import json
import subprocess as sub

def parseCommandLine():
    """Parse command line arguments."""

    PARSER = argparse.ArgumentParser(
                                     description="Simple wrapper for Readium Go Rwp")

    PARSER.add_argument("pathIn",
                        action="store",
                        type=str,
                        help="input directory")
    PARSER.add_argument("pathOut",
                        action="store",
                        type=str,
                        help="output directory")
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
    pathIn = os.path.abspath(args.pathIn)
    # Output path
    pathOut = os.path.abspath(args.pathOut)
    # Output prefix
    prefixOut = args.prefixOut

    # Output files
    tarOut = os.path.join(pathOut, ("{}.tar").format(prefixOut))
    logOut = os.path.join(pathOut, ("{}.log").format(prefixOut))

    # Set up logging config (stderr + file)
    logging.basicConfig(format='%(levelname)s: %(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        handlers=[logging.FileHandler(logOut),
                                  logging.StreamHandler()
                        ],
                        level=logging.DEBUG)

    logging.info('### SESSION START')

    # Temporary output files file info and Rwp
    fileInfoTemp = os.path.join(pathOut, 'fileinfotemp.json')
    rwpOutTemp = os.path.join(pathOut, 'rwptemp.json')

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

    try:
        with tarfile.open(tarOut, "r") as tf:
            # List of all current paths inside TAR
            tarPaths = tf.getnames()
    except IOError:
        tarPaths = []

    counter = 1

    for ebook in ebooksIn:

        # Construct TAR output paths
        fPath, fName = os.path.split(ebook)
        dirIn = os.path.basename(fPath)
        logging.info('*****')
        logging.info(('file {}/{}').format(str(counter), str(noEbooks)))
        logging.info(fName)
        tarPath = os.path.join(dirIn)
        tarOutInfo = os.path.join(tarPath, nameInfo)
        tarOutRwp = os.path.join(tarPath, nameOutRwp)

        # Open TAR archive
        with tarfile.open(tarOut, "a") as tf:
            rwpCommand = ""
            rwpStatus = ""
            # Only process current file if path doesn't already exist
            # This also means duplicates of already processed files will
            # be skipped!
            if tarPath not in tarPaths:
                # Run Rwp
                rwpResult = runRwp(rwp, ebook, rwpOutTemp)
                if rwpResult["status"] in [0, 1]:
                    tf.add(rwpOutTemp, arcname=tarOutRwp)
                    tarPaths.append(tarPath)
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
