#!/bin/sh
#
#
# Extract i18n messages from python source and create pys.pot file
pygettext.py -d pysql -p po *.py

for lang in $(ls po | grep -v .pot)
do
    # Merge pot and po files
    msgmerge -U po/${lang}/pysql.po po/pysql.pot

    # Generate mo files
    msgfmt.py -o locale/${lang}/LC_MESSAGES/pysql.mo po/${lang}/pysql.po
done

# Compile file
msgfmt -o locale/fr/LC_MESSAGES/pysql.mo po/fr/pysql.po
