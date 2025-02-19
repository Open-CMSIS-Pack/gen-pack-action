#!/usr/bin/env bash

PACKCHK=$(which packchk)
if [ -z "$PACKCHK" ]; then
  echo "::error::packchk not found"
  exit 1
fi

PACKCHK_VERSION=$(${PACKCHK} --version | grep -oE "packchk [0-9.]+" | grep -oE "[0-9.]+")
if [[ "$PACKCHK_VERSION" != "1.4.1" ]]; then
  echo "::error::packchk version 1.4.1 expected, found $PACKCHK_VERSION"
  exit 1
fi

if [ ! -f "${CMSIS_PACK_ROOT}/.Web/ARM.CMSIS.pdsc" ]; then
    echo "::error::ARM.CMSIS.pdsc not found"
    exit 1
fi

echo "Simulating doxygen warnings..."
# <file>:<line>: warning: <message> (see doxygen.json)
echo 'doc.txt:35: warning: Found unknown command "foo".'

echo "Simulating linkchecker warnings..."
# <file>:<line>:<column>;<url>;<code>;<message> (see linkchecker.json)
echo 'doc.txt:40:12;http://example.com;404;The requested URL was not found on this server.'

echo "Simulating packchk warnings..."
# *** <severity> M<code>: <file> (Line <line>) (see packchk.json)
#   <message>
echo '*** INFO M0001: Vendor.Pack.pdsc (Line 1)'
echo '  This is an informational message.'
echo ''
echo '*** WARNING M0002: Vendor.Pack.pdsc (Line 2)'
echo '  This is a warning message.'
echo ''
echo '*** ERROR M0003: Vendor.Pack.pdsc (Line 3)'
echo '  This is an error message.'
echo ''

# Creating output

mkdir -p output
touch "Vendor.Pack.1.0.0.pack"

exit 0
