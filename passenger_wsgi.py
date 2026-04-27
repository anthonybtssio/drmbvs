import sys
import os

# Ajoute le répertoire actuel au path pour que Python trouve app.py
sys.path.insert(0, os.path.dirname(__file__))

from app import app as application
