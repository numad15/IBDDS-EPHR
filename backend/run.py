"""
Entry point for running the IBDDS EPHR backend server locally.
Usage: python run.py
"""

from src.api.server import run_server

if __name__ == '__main__':
    run_server()
