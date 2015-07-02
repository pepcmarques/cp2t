# CP2T: Convert PDF to text (keeping table)

About
=====
This program use some existing tools to convert from PDF to TEXT or HTML keeping tables

Pre requisites
==============
Libraries needed:
   - OpenCV (http://opencv.org/) -> OpenCV depends on numpy and scipy
   - BeautifulSoup (http://www.crummy.com/software/BeautifulSoup/)
   - Pillow (https://github.com/python-pillow/Pillow)
   - tempfile 

   In Debian like flavors a "apt-get install" would works

Installation
============
Just copy cp2t.py to your work directory

Examples
========
It works as command line or importing it.

- Command line

python cp2t.py -i <input file> -o <output file> [-t] [-d] [-f [text|html]]

-i = input file (i.e. PDF file)
-o = output file
-t = it will try to find tables (default is False)
-d = debug (default is False)
-f = output format (default is text)

- Importing

import cp2t

output = cp2t_v5.converte(_inputfile=nomefilein, _outputfile=nomefileout, _tables=True, _debug=False, _format="text")

Obs.: Cell delimiter for text format is "_||_" (without quotes)

TO DO
=====
- Translate variables to make the program easier to be read
- Improve built_text method (close_table is not working in all cases for HTML)
- Improve, improve, improve...

