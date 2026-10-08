from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sqlite3
from urllib.parse import urlparse

DB_NAME = "knowledge_base.db"

# Simple demo permissions
TOKENS = {
    "admin-token": "admin",
    "user-token": "user"
}


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            owner TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def get_documents():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM documents ORDER BY id DESC")
    documents = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return documents


def get_document(document_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM documents WHERE id = ?",
        (document_id,)
    )

    document = cursor.fetchone()
    conn.close()

    return dict(document) if document else None


class KnowledgeBaseAPI(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        response = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()

        self.wfile.write(response)

    def get_user(self):
        auth = self.headers.get("Authorization", "")

        if not auth.startswith("Bearer "):
            return None

        token = auth.replace("Bearer ", "", 1).strip()
        return TOKENS.get(token)

    def read_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            return json.loads(body)
        except Exception:
            return None

    def do_GET(self):
        path = urlparse(self.path).path

        # List all documents
        if path == "/api/knowledge-base":
            documents = get_documents()
            self.send_json({
                "success": True,
                "documents": documents
            })
            return

        # Get single document
        if path.startswith("/api/knowledge-base/"):
            try:
                document_id = int(path.split("/")[-1])
            except ValueError:
                self.send_json(
                    {"error": "Invalid document ID"},
                    400
                )
                return

            document = get_document(document_id)

            if not document:
                self.send_json(
                    {"error": "Document not found"},
                    404
                )
                return

            self.send_json({
                "success": True,
                "document": document
            })
            return

        self.send_json({"error": "Endpoint not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/api/knowledge-base":
            self.send_json({"error": "Endpoint not found"}, 404)
            return

        user = self.get_user()

        if not user:
            self.send_json(
                {"error": "Unauthorized. Valid token required."},
                401
            )
            return

        data = self.read_body()

        if not data:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        title = str(data.get("title", "")).strip()
        content = str(data.get("content", "")).strip()

        # Validation
        if not title:
            self.send_json(
                {"error": "Title is required"},
                400
            )
            return

        if not content:
            self.send_json(
                {"error": "Content is required"},
                400
            )
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO documents (title, content, owner)
            VALUES (?, ?, ?)
            """,
            (title, content, user)
        )

        document_id = cursor.lastrowid

        conn.commit()
        conn.close()

        self.send_json({
            "success": True,
            "message": "Knowledge base document created",
            "document_id": document_id
        }, 201)

    def do_PUT(self):
        path = urlparse(self.path).path

        if not path.startswith("/api/knowledge-base/"):
            self.send_json({"error": "Endpoint not found"}, 404)
            return

        user = self.get_user()

        if not user:
            self.send_json(
                {"error": "Unauthorized. Valid token required."},
                401
            )
            return

        try:
            document_id = int(path.split("/")[-1])
        except ValueError:
            self.send_json(
                {"error": "Invalid document ID"},
                400
            )
            return

        document = get_document(document_id)

        if not document:
            self.send_json(
                {"error": "Document not found"},
                404
            )
            return

        # Only admin or document owner can update
        if user != "admin" and document["owner"] != user:
            self.send_json(
                {"error": "Permission denied"},
                403
            )
            return

        data = self.read_body()

        if not data:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        title = str(data.get("title", "")).strip()
        content = str(data.get("content", "")).strip()

        if not title or not content:
            self.send_json(
                {"error": "Title and content are required"},
                400
            )
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE documents
            SET title = ?, content = ?
            WHERE id = ?
            """,
            (title, content, document_id)
        )

        conn.commit()
        conn.close()

        self.send_json({
            "success": True,
            "message": "Document updated successfully"
        })

    def do_DELETE(self):
        path = urlparse(self.path).path

        if not path.startswith("/api/knowledge-base/"):
            self.send_json({"error": "Endpoint not found"}, 404)
            return

        user = self.get_user()

        if not user:
            self.send_json(
                {"error": "Unauthorized. Valid token required."},
                401
            )
            return

        try:
            document_id = int(path.split("/")[-1])
        except ValueError:
            self.send_json(
                {"error": "Invalid document ID"},
                400
            )
            return

        document = get_document(document_id)

        if not document:
            self.send_json(
                {"error": "Document not found"},
                404
            )
            return

        # Only admin or document owner can delete
        if user != "admin" and document["owner"] != user:
            self.send_json(
                {"error": "Permission denied"},
                403
            )
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM documents WHERE id = ?",
            (document_id,)
        )

        conn.commit()
        conn.close()

        self.send_json({
            "success": True,
            "message": "Document deleted successfully"
        })


if __name__ == "__main__":
    init_db()

    server = HTTPServer(
        ("localhost", 8000),
        KnowledgeBaseAPI
    )

    print("Knowledge Base API running on http://localhost:8000")
    print("Admin token: admin-token")
    print("User token: user-token")

    server.serve_forever()
