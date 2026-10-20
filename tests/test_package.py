"""Verify the actual ZIP users install, including its copied math core."""
from pathlib import Path
import subprocess
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class InstallablePackage(unittest.TestCase):
    def test_release_zip_contains_the_addon_and_current_solver(self):
        subprocess.run([sys.executable, str(ROOT / 'scripts/make_addon.py')], check=True)
        with zipfile.ZipFile(ROOT / 'linkage_studio.zip') as package:
            self.assertIsNone(package.testzip())
            self.assertEqual(set(package.namelist()), {
                'linkage_studio/__init__.py',
                'linkage_studio/builder.py',
                'linkage_studio/linkage.py',
            })
            self.assertEqual(package.read('linkage_studio/linkage.py'), (ROOT / 'linkage.py').read_bytes())
            for filename in ['__init__.py', 'builder.py']:
                self.assertEqual(package.read('linkage_studio/' + filename), (ROOT / 'linkage_studio' / filename).read_bytes())


if __name__ == '__main__':
    unittest.main()
