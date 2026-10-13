import json
import tempfile
import unittest
from pathlib import Path

from app import create_app


class MindVaultApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "mindvault.sqlite3"
        self.app = create_app({
            "TESTING": True,
            "DATABASE": str(database_path),
            "KNOWLEDGE_ENGINE_PATH": str(Path(self.temp_dir.name) / "missing-engine"),
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_note(
        self, title="Cell membranes", content="Selective barrier", subject="Biology", tags=None
    ):
        return self.client.post("/api/notes", json={
            "title": title,
            "content": content,
            "subject": subject,
            "tags": tags if tags is not None else ["cells", "revision"],
        })

    def test_create_edit_delete_note(self):
        created = self.create_note()
        self.assertEqual(created.status_code, 201)
        note_id = created.get_json()["id"]

        edited = self.client.put(f"/api/notes/{note_id}", json={
            "title": "Membrane transport",
            "content": "Diffusion and osmosis",
            "subject": "Biology",
            "tags": ["transport"],
        })
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.get_json()["title"], "Membrane transport")

        deleted = self.client.delete(f"/api/notes/{note_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get("/api/notes").get_json(), [])

    def test_search_matches_title_content_and_tags(self):
        self.create_note("Cell membranes", "Selective barrier", "Biology")
        self.create_note("Linear equations", "Solve for x", "Math", ["algebra"])

        response = self.client.get("/api/notes?q=barrier")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([note["title"] for note in response.get_json()], ["Cell membranes"])
        tagged = self.client.get("/api/notes?q=revision")
        self.assertEqual(len(tagged.get_json()), 1)

    def test_notes_persist_across_app_instances(self):
        created = self.create_note()
        database_path = self.app.config["DATABASE"]
        second_app = create_app({
            "TESTING": True,
            "DATABASE": database_path,
            "KNOWLEDGE_ENGINE_PATH": str(Path(self.temp_dir.name) / "missing-engine"),
        })
        response = second_app.test_client().get("/api/notes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()[0]["id"], created.get_json()["id"])

    def test_api_rejects_invalid_note_data(self):
        missing_title = self.client.post("/api/notes", json={"content": "No title"})
        self.assertEqual(missing_title.status_code, 400)
        self.assertIn("error", missing_title.get_json())

        too_many_tags = self.client.post("/api/notes", json={
            "title": "Valid title",
            "tags": [f"tag-{index}" for index in range(11)],
        })
        self.assertEqual(too_many_tags.status_code, 400)

        invalid_json = self.client.post(
            "/api/notes", data="not json", content_type="application/json"
        )
        self.assertEqual(invalid_json.status_code, 400)

    def test_stats_fall_back_when_c_engine_is_missing(self):
        self.create_note()
        response = self.client.get("/api/stats")
        self.assertEqual(response.status_code, 200)
        stats = response.get_json()
        self.assertEqual(stats["note_count"], 1)
        self.assertEqual(stats["subject_count"], 1)
        self.assertEqual(stats["score_engine"], "python")
        self.assertGreater(stats["learning_score"], 0)

    def test_home_page_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"MindVault", response.data)


if __name__ == "__main__":
    unittest.main()
