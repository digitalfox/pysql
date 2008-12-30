#!/bin/sh
#
#
# Extract i18n messages from python source and create pys.pot file

cd $(dirname $0)/..

pygettext.py -d pysql -p po src/pysql/*.py

for lang in $(ls po | grep -v .pot)
do
    # Merge pot and po files
    msgmerge -U po/${lang}/pysql.po po/pysql.pot

    # Generate mo files
    msgfmt.py -o src/share/locale/${lang}/LC_MESSAGES/pysql.mo po/${lang}/pysql.po
done
