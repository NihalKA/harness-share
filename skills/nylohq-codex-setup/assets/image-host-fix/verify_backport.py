"""Offline regression checks for the upstream image-host backport."""

import unittest
from unittest.mock import Mock, patch

from app.core.openai import host_models
from app.core.openai.images import V1ImagesGenerationsRequest
from app.modules.proxy import api, images_service


class ImageHostBackportTests(unittest.TestCase):
    def resolve(self, available, suppressed=()):
        registry = Mock()
        registry.plan_types_for_model.side_effect = lambda slug: (
            frozenset({"pro"}) if slug in available else frozenset()
        )
        registry.is_suppressed_model.side_effect = lambda slug: slug in suppressed
        with patch.object(host_models, "get_model_registry", return_value=registry):
            return host_models.resolve_default_host_model()

    def test_removed_legacy_host_uses_available_current_model(self):
        self.assertEqual(self.resolve({"gpt-5.6-luna"}), "gpt-5.6-luna")

    def test_suppressed_current_host_uses_available_legacy_model(self):
        self.assertEqual(
            self.resolve({"gpt-5.6-luna", "gpt-5.5"}, {"gpt-5.6-luna"}),
            "gpt-5.5",
        )

    def test_empty_registry_keeps_upstream_current_default(self):
        self.assertEqual(self.resolve(set()), "gpt-5.6-luna")

    def test_generation_retains_public_image_model(self):
        host = self.resolve({"gpt-5.6-luna"})
        request = images_service.images_generation_to_responses_request(
            V1ImagesGenerationsRequest(
                model="gpt-image-2", prompt="A simple abstract banner."
            ),
            host_model=host,
        )
        payload = request.model_dump(mode="json")
        self.assertEqual(payload["model"], "gpt-5.6-luna")
        self.assertEqual(payload["tools"][0]["model"], "gpt-image-2")
        self.assertEqual(payload["tool_choice"], {"type": "image_generation"})
        self.assertTrue(payload["stream"])

    def test_route_import_uses_shared_resolver(self):
        self.assertIs(api.resolve_default_host_model, host_models.resolve_default_host_model)


if __name__ == "__main__":
    unittest.main(verbosity=2)
