#!/usr/bin/env bash

DOXYGEN=$(which doxygen)
if [ -z "$DOXYGEN" ]; then
    echo "::error::doxygen not found"
    exit 1
fi

DOXYGEN_VERSION=$(${DOXYGEN} --version | grep -oE '^[0-9.]+')
if [[ "$DOXYGEN_VERSION" != "1.9.6" ]]; then
    echo "::error::doxygen version 1.9.6 expected, found $DOXYGEN_VERSION"
    exit 1
fi

LINKCHECKER=$(which linkchecker)
if [ -z "$LINKCHECKER" ]; then
    echo "::error::linkchecker not found"
    exit 1
fi

LINKCHECKER_EXPECTED_VERSION=$(pip show linkchecker | grep "Version:" | grep -oE "[0-9.]+")
LINKCHECKER_VERSION=$(${LINKCHECKER} --version | grep -oE "LinkChecker [0-9.]+" | grep -oE "[0-9.]+")
if [[ "${LINKCHECKER_VERSION}" != "${LINKCHECKER_EXPECTED_VERSION}" ]]; then
    echo "::error::linkchecker version ${LINKCHECKER_EXPECTED_VERSION} expected, found ${LINKCHECKER_VERSION}"
    exit 1
fi


echo "Simulating doxygen warnings..."
# <file>:<line>: warning: <message> (see doxygen.json)
echo 'doc.txt:25: warning: Found unknown command "foo".'

echo "Simulating linkchecker warnings..."
# <file>:<line>:<column>;<url>;<code>;<message> (see linkchecker.json)
echo 'doc.txt:30:10;http://example.com;404;The requested URL was not found on this server.'

echo "Creating output"
mkdir -p Documentation/html
touch Documentation/html/index.html

exit 0
