import os
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from dotenv import load_dotenv

# Load .env
load_dotenv(Path(__file__).parent / '.env')

from app.config import VOICEPRINTS_ROOT
from app.engine import try_build_enrollment_from_voiceprints_root

print('VOICEPRINTS_ROOT:', VOICEPRINTS_ROOT)

if VOICEPRINTS_ROOT:
    result = try_build_enrollment_from_voiceprints_root('2')
    print('try_build result:', result)
else:
    print('VOICEPRINTS_ROOT is None')