import unittest
import os
import tempfile
from dualsense_to_desmume import generate_config_dict, update_ini_file, DEFAULT_MAPPINGS

class TestDualSenseToDesmume(unittest.TestCase):

    def test_generate_config_dict_default(self):
        config = generate_config_dict(DEFAULT_MAPPINGS, joystick_index=0)
        self.assertEqual(config["Joypad1.A"], "0x4002")
        self.assertEqual(config["Joypad1.Up"], "0x4100")

    def test_generate_config_dict_index_1(self):
        config = generate_config_dict(DEFAULT_MAPPINGS, joystick_index=1)
        self.assertEqual(config["Joypad2.A"], "0x8002")
        self.assertEqual(config["Joypad2.Up"], "0x8100")

    def test_update_ini_file_non_destructive(self):
        initial_content = "[Joypad]\nJoypad1.A=123\nJoypad2.A=456\n"
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write(initial_content)
            tmp_path = tmp.name

        try:
            new_config = {"Joypad1.A": "0x4002", "Joypad1.B": "0x4001"}
            success, msg = update_ini_file(tmp_path, new_config, joystick_index=0)
            self.assertTrue(success)

            with open(tmp_path, 'r') as f:
                content = f.read()

            self.assertIn("Joypad1.A=0x4002", content)
            self.assertIn("Joypad1.B=0x4001", content)
            self.assertIn("Joypad2.A=456", content)
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)
            if os.path.exists(tmp_path + ".bak"): os.remove(tmp_path + ".bak")

if __name__ == '__main__':
    unittest.main()
