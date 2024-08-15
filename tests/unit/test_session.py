import pytest
import sys
import os
from unittest.mock import patch, MagicMock, mock_open

# Add the src directory to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from ublue_update.session import get_active_sessions, get_xdg_runtime_dir

# @patch("ublue_update.session.subprocess.run")