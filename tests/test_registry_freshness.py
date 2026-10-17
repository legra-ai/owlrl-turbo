"""A newly published exact dependency must supersede a cached empty index."""

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def make_wheel(root, name, requires=None):
    filename = f"{name}-0.1.0a2-py3-none-any.whl"
    metadata = f"Metadata-Version: 2.4\nName: {name.replace('_', '-')}\nVersion: 0.1.0a2\n"
    if requires:
        metadata += f"Requires-Dist: {requires}\n"
    dist_info = f"{name}-0.1.0a2.dist-info"
    with zipfile.ZipFile(root / filename, "w") as archive:
        archive.writestr(f"{dist_info}/METADATA", metadata + "\n")
        archive.writestr(
            f"{dist_info}/WHEEL",
            "Wheel-Version: 1.0\nGenerator: regression\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        archive.writestr(f"{dist_info}/RECORD", "")
    return root / filename


def test_install_refreshes_metadata_after_dependency_publication(tmp_path, monkeypatch):
    uv = shutil.which("uv")
    assert uv is not None, "Wheel verification requires uv"
    runtime = make_wheel(tmp_path, "freshness_runtime")
    consumer = make_wheel(tmp_path, "freshness_consumer", "freshness-runtime==0.1.0a2")
    state = {"published": False, "index_reads": 0}

    class Index(BaseHTTPRequestHandler):
        def do_GET(self):
            self.serve(send_body=True)

        def do_HEAD(self):
            self.serve(send_body=False)

        def serve(self, *, send_body):
            if self.path == "/simple/freshness-runtime/":
                state["index_reads"] += 1
                link = ""
                if state["published"]:
                    digest = hashlib.sha256(runtime.read_bytes()).hexdigest()
                    link = f'<a href="/{runtime.name}#sha256={digest}">{runtime.name}</a>'
                payload = f"<!doctype html><html><body>{link}</body></html>".encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Cache-Control", "max-age=3600")
            elif self.path == f"/{runtime.name}":
                payload = runtime.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
            else:
                self.send_error(404)
                return
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if send_body:
                self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Index)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("UV_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setenv("UV_DEFAULT_INDEX", f"http://127.0.0.1:{server.server_port}/simple/")
        monkeypatch.delenv("UV_INDEX_URL", raising=False)
        monkeypatch.delenv("UV_EXTRA_INDEX_URL", raising=False)
        project = tmp_path / "project"
        subprocess.run(
            [
                uv,
                "init",
                "--bare",
                "--no-workspace",
                "--vcs",
                "none",
                "--python",
                sys.executable,
                str(project),
            ],
            check=True,
        )
        initial = subprocess.run(
            [uv, "add", "--no-sync", "--project", str(project), str(consumer)],
            capture_output=True,
            text=True,
        )
        assert initial.returncode != 0
        assert "freshness-runtime" in initial.stderr
        assert state["index_reads"] == 1
        state["published"] = True

        spec = importlib.util.spec_from_file_location(
            "wheel_install", Path(__file__).parents[1] / "scripts/wheel_install.py"
        )
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        installer.install_wheel(project, consumer, test_extra=False)

        assert state["index_reads"] >= 2
        observed = subprocess.check_output(
            [
                uv,
                "run",
                "--project",
                str(project),
                "--locked",
                "python",
                "-c",
                "import importlib.metadata as m, json; print(json.dumps(m.version('freshness-runtime')))",
            ],
            text=True,
        )
        assert json.loads(observed) == "0.1.0a2"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
