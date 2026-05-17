"""Корневой conftest.py — добавляет корень проекта в sys.path для импортов src.*"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
