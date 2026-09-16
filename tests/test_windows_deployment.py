from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WINDOWS_DEPLOYMENT = ROOT / "deploy" / "windows"


class WindowsDeploymentContractTests(unittest.TestCase):
    def _read(self, name: str) -> str:
        return (WINDOWS_DEPLOYMENT / name).read_text(encoding="utf-8")

    def test_required_windows_deployment_files_exist(self) -> None:
        expected = {
            "Install-Jarvis.ps1",
            "Jarvis.Windows.ps1",
            "README.md",
            "Remove-JarvisTask.ps1",
            "Start-Jarvis.ps1",
            "Test-Jarvis.ps1",
        }
        self.assertEqual(
            {path.name for path in WINDOWS_DEPLOYMENT.iterdir() if path.is_file()},
            expected,
        )

    def test_startup_contract_is_production_local_only_and_single_worker(self) -> None:
        helper = self._read("Jarvis.Windows.ps1")
        startup = self._read("Start-Jarvis.ps1")

        self.assertIn('JARVIS_ENV"] -ne "production"', helper)
        self.assertIn('JARVIS_BIND_HOST"] -ne "127.0.0.1"', helper)
        self.assertIn('JARVIS_AUDIT_PERSISTENT"].ToLowerInvariant()', helper)
        self.assertIn("--workers 1", startup)
        self.assertIn("--no-access-log", startup)
        self.assertIn('Join-Path $runtimeRoot "service.log"', startup)
        self.assertNotIn("0.0.0.0", helper + startup)

    def test_installer_generates_secret_and_registers_restarting_logon_task(self) -> None:
        installer = self._read("Install-Jarvis.ps1")

        self.assertIn("RandomNumberGenerator", installer)
        self.assertIn("icacls.exe", installer)
        self.assertIn("New-ScheduledTaskTrigger -AtLogOn", installer)
        self.assertIn("-MultipleInstances IgnoreNew", installer)
        self.assertIn("-RestartCount 3", installer)
        self.assertIn("Test-Jarvis.ps1", installer)
        self.assertIn("-m compileall -q", installer)
        self.assertNotIn("JARVIS_API_TOKEN=test", installer)

    def test_smoke_test_does_not_expose_token_as_process_argument(self) -> None:
        smoke_test = self._read("Test-Jarvis.ps1")

        self.assertIn('SetEnvironmentVariable("JARVIS_BASE_URL"', smoke_test)
        self.assertNotIn("--token", smoke_test)

    def test_removal_preserves_configuration_and_audit_data(self) -> None:
        removal = self._read("Remove-JarvisTask.ps1")

        self.assertIn("Unregister-ScheduledTask", removal)
        self.assertNotIn("Remove-Item", removal)


if __name__ == "__main__":
    unittest.main()
