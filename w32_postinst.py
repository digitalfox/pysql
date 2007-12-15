#!/usr/bin/python
# -*- coding: utf-8 -*-

# Sébastien Renard (sebastien.renard@digitalfox.org)
# Code licensed under GNU GPL V2


""" Post installation script for win32 system
    Thanks to the coin coin projet for the inspiration for this postinstall script
"""

from os.path import abspath, join
from os import mkdir
import sys

# pylint: disable-msg=E0602

# Description string
desc="PySQL - advanced Oracle client written in Python"
# Shortcut name
lnk="pysql.lnk"

# Only do things at install stage, not uninstall
if sys.argv[1] == "-install":
    # Get python.exe path
    py_path = abspath(join(sys.prefix, "python.exe"))
    
    # Pysql wrapper path
    pysql_dir=abspath(join(sys.prefix, "scripts"))
    pysql_path=join(pysql_dir, "pysql")
                          
    #TODO: create a sexy pysql .ico file to be put in share dir
    
    
    # Find desktop    
    try:
        desktop_path = get_special_folder_path("CSIDL_COMMON_DESKTOPDIRECTORY")
    except OSError:
        desktop_path = get_special_folder_path("CSIDL_DESKTOPDIRECTORY")
    
    # Desktop shortcut creation
    create_shortcut(py_path, # program to launch
                    desc,
                    join(desktop_path, lnk),  # shortcut file
                    pysql_path, # Argument (pythohn script)
                    pysql_dir, # Current work dir
                    "" # Ico file (nothing for now)
                    )

    # Tel install process that we create a file so it can removed it during uninstallation
    file_created(join(desktop_path, lnk))

    # Start menu shortcut creation
    try:
        start_path = get_special_folder_path("CSIDL_COMMON_PROGRAMS")
    except OSError:
        start_path = get_special_folder_path("CSIDL_PROGRAMS")

    # Création du dossier dans le menu programme
    programs_path = join(start_path, "PySQL")
    try:
        mkdir(programs_path)
    except OSError:
        pass
    directory_created(programs_path)

    create_shortcut(py_path, # program to launch
                    desc, 
                    join(programs_path, lnk),  # Shortcut file
                    pysql_path, # Argument (python script)
                    pysql_dir, # Cuurent work dir
                    "" # Icone
                    )
    file_created(join(programs_path, lnk))

    # End of script
    sys.exit()