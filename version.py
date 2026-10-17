"""
LSDM - Laboratory Sample & Dispatch Management System
Centralized Version Configuration
"""

__version__ = "1.0.0"
__app_name__ = "LSDM"
__full_name__ = "Laboratory Sample & Dispatch Management System"
__build_date__ = "2026-10-17"
__author__ = "Lab Operations & Supply Chain Solutions"
__repo__ = "https://github.com/your-username/LSDM"

def get_version_info() -> dict:
    return {
        "version": __version__,
        "app_name": __app_name__,
        "full_name": __full_name__,
        "build_date": __build_date__,
        "author": __author__,
        "repo": __repo__
    }
