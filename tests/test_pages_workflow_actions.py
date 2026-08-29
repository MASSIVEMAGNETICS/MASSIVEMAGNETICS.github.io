from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PagesWorkflowActionGenerationTests(unittest.TestCase):
    def _read(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_registry_uses_current_checkout_and_python_actions(self) -> None:
        workflow = self._read(".github/workflows/registry.yml")
        self.assertIn("uses: actions/checkout@v7", workflow)
        self.assertIn("uses: actions/setup-python@v7", workflow)
        self.assertNotIn("uses: actions/checkout@v6", workflow)
        self.assertNotIn("uses: actions/setup-python@v6", workflow)

    def test_primary_and_recovery_deployments_share_pages_action_generation(self) -> None:
        for relative_path in (
            ".github/workflows/deploy.yml",
            ".github/workflows/post-deploy-verify.yml",
        ):
            with self.subTest(workflow=relative_path):
                workflow = self._read(relative_path)
                self.assertIn("uses: actions/upload-pages-artifact@v5", workflow)
                self.assertIn("uses: actions/deploy-pages@v5", workflow)
                self.assertNotIn("uses: actions/upload-pages-artifact@v4", workflow)
                self.assertNotIn("uses: actions/deploy-pages@v4", workflow)

    def test_primary_and_recovery_paths_keep_same_pages_action_versions(self) -> None:
        deploy = self._read(".github/workflows/deploy.yml")
        recovery = self._read(".github/workflows/post-deploy-verify.yml")
        expected = (
            "actions/configure-pages@v6",
            "actions/upload-pages-artifact@v5",
            "actions/deploy-pages@v5",
        )
        for action in expected:
            with self.subTest(action=action):
                self.assertIn(action, deploy)
                self.assertIn(action, recovery)

    def test_pages_uploads_include_well_known_identity_files(self) -> None:
        for relative_path in (
            ".github/workflows/deploy.yml",
            ".github/workflows/post-deploy-verify.yml",
        ):
            with self.subTest(workflow=relative_path):
                workflow = self._read(relative_path)
                upload_marker = "uses: actions/upload-pages-artifact@v5"
                self.assertIn(upload_marker, workflow)
                upload_section = workflow.split(upload_marker, 1)[1].split("uses: actions/deploy-pages@v5", 1)[0]
                self.assertIn("include-hidden-files: true", upload_section)

    def test_site_builder_emits_well_known_identity_manifest(self) -> None:
        builder = self._read("tools/build_site.py")
        self.assertIn('well_known = output / ".well-known"', builder)
        self.assertIn('(well_known / "iambandobandz.json").write_text(', builder)


if __name__ == "__main__":
    unittest.main(verbosity=2)
