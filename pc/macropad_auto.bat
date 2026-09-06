@echo off
REM Lance le compagnon du macropad. Double-clique sur ce fichier.
REM Si Python n'est pas trouve, installe-le depuis python.org en cochant
REM "Add Python to PATH", puis fais :  py -m pip install pyserial
cd /d "%~dp0"
REM %* transmet les options recues (par exemple --journal,
REM que le raccourci de demarrage automatique ajoute).
py macropad_auto.py %*
pause
