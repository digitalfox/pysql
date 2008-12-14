#/bin/sh
# Update doc
cd $(dirname $0)/..
epydoc --name=pysql --graph=all --html -o doc/ src/pysql/*py
