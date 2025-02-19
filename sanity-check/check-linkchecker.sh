#!/usr/bin/env bash

LINKCHECKER=$(which linkchecker)
if [ -z "$LINKCHECKER" ]; then
    echo "::error::linkchecker not found"
    exit 1
fi

EXPECTED_VERSION=$(pip info linkchecker | grep "Version:" | grep -oE "[0-9.]+")

VERSION=$(${LINKCHECKER} --version)
if [[ "$VERSION" != "$EXPECTED_VERSION" ]]; then
    echo "::error::linkchecker version $EXPECTED_VERSION expected, found $VERSION"
    exit 1
fi

echo "Simulating linkchecker warnings..."
# <file>:<line>:<column>;<url>;<code>;<message> (see linkchecker.json)
echo 'doc.txt:50:23;http://example.com;404;The requested URL was not found on this server.'

exit 0
