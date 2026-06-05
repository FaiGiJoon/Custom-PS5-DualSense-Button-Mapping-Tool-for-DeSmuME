import unittest
import os
import tempfile
from dualsense_to_desmume import generate_config_dict, update_ini_file, DEFAULT_MAPPINGS, find_desmume_ini

class TestDualSenseToDesmume(unittest.TestCase):

    def test_generate_config_dict_default(self):
        config = generate_config_dict(DEFAULT_MAPPINGS, joystick_index=0)
        self.assertEqual(config["Joypad1.A"], "0x4002")
        self.assertEqual(config["Joypad1.Up"], "0x4100")
        self.assertEqual(config["Joypad1.Right"], "0x4101")

    def test_generate_config_dict_index_1(self):
        # Joystick index 1 should be (1+1) << 14 = 0x8000
        # Hat should be 0x8100
        # Prefix should be Joypad2
        config = generate_config_dict(DEFAULT_MAPPINGS, joystick_index=1)
        self.assertEqual(config["Joypad2.A"], "0x8002")
        self.assertEqual(config["Joypad2.Up"], "0x8100")

    def test_update_ini_file_non_destructive(self):
        # Create a dummy ini file with multiple joypads
        initial_content = (
            "[OtherSection]\n"
            "Key=Value\n"
            "\n"
            "[Joypad]\n"
            "Joypad1.A=123\n"
            "Joypad2.A=456\n"
            "\n"
            "[Another]\n"
            "Foo=Bar"
        )
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write(initial_content)
            tmp_path = tmp.name

        try:
            new_config = {"Joypad1.A": "0x4002", "Joypad1.B": "0x4001"}
            success, msg = update_ini_file(tmp_path, new_config, joystick_index=0)
            self.assertTrue(success)
            self.assertIn("Successfully updated", msg)

            with open(tmp_path, 'r') as f:
                content = f.read()

            self.assertIn("[OtherSection]", content)
            self.assertIn("[Joypad]", content)
            self.assertIn("Joypad1.A=0x4002", content)
            self.assertIn("Joypad1.B=0x4001", content)
            self.assertIn("Joypad2.A=456", content) # Joypad2 should be preserved
            self.assertIn("[Another]", content)
            self.assertNotIn("Joypad1.A=123", content)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(tmp_path + ".bak"):
                os.remove(tmp_path + ".bak")

    def test_update_ini_file_append_joypad2(self):
        initial_content = "[Joypad]\nJoypad1.A=0x4002\n"
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write(initial_content)
            tmp_path = tmp.name

        try:
            new_config = {"Joypad2.A": "0x8002"}
            success, msg = update_ini_file(tmp_path, new_config, joystick_index=1)
            self.assertTrue(success)

            with open(tmp_path, 'r') as f:
                content = f.read()

            self.assertIn("Joypad1.A=0x4002", content)
            self.assertIn("Joypad2.A=0x8002", content)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(tmp_path + ".bak"):
                os.remove(tmp_path + ".bak")

    def test_find_desmume_ini(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ini_path = os.path.join(tmpdir, "desmume.ini")
            with open(ini_path, 'w') as f:
                f.write("[Joypad]")

            # Test finding it with explicit exe_path hint
            found = find_desmume_ini(os.path.join(tmpdir, "desmume.exe"))
            self.assertEqual(found, ini_path)

            # Test finding it when in current directory
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                found = find_desmume_ini()
                self.assertEqual(os.path.abspath(found), os.path.abspath(ini_path))
            finally:
                os.chdir(old_cwd)

if __name__ == '__main__':
    unittest.main()
