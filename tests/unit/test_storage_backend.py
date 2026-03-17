"""
Unit tests for LocalStorageBackend and S3StorageBackend.
Uses temp dirs for local storage; mocks boto3 via sys.modules for S3 tests
(boto3 is a Docker-only dependency not installed on the host test runner).
"""
import os
import sys
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, call

from src.backend.services.storage import (
    LocalStorageBackend,
    get_storage_backend,
)


# ─── helpers ────────────────────────────────────────────────────────────────

def _local(tmp_path):
    with patch("src.backend.services.storage.settings") as s:
        s.ENV = "development"
        return LocalStorageBackend(str(tmp_path / "uploads"))


def _make_mock_boto3(head_raises=False, create_raises=False):
    mock_client = MagicMock()
    if head_raises:
        mock_client.head_bucket.side_effect = Exception("bucket not found")
    else:
        mock_client.head_bucket.return_value = {}
    if create_raises:
        mock_client.create_bucket.side_effect = Exception("access denied")
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_client
    return mock_boto3, mock_client


def _s3_backend(head_raises=False, create_raises=False, endpoint_url=None, bucket="test-bucket"):
    mock_boto3, mock_client = _make_mock_boto3(head_raises, create_raises)
    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        with patch("src.backend.services.storage.settings") as s:
            s.AWS_ACCESS_KEY_ID = "FAKEKEY"
            s.AWS_SECRET_ACCESS_KEY = "FAKESECRET"
            s.AWS_REGION = "us-east-1"
            s.S3_ENDPOINT_URL = endpoint_url
            s.S3_BUCKET_NAME = bucket
            from src.backend.services.storage import S3StorageBackend
            backend = S3StorageBackend()
    backend.client = mock_client
    backend.bucket = bucket
    return backend


# ─── LocalStorageBackend ────────────────────────────────────────────────────

class TestLocalStorageBackend:
    def test_upload_stores_bytes(self, tmp_path):
        backend = _local(tmp_path)
        key = backend.upload("photo.jpg", b"\xFF\xD8\xFF")
        assert key == "photo.jpg"
        assert (tmp_path / "uploads" / "photo.jpg").exists()

    def test_upload_nested_key_creates_directories(self, tmp_path):
        backend = _local(tmp_path)
        backend.upload("2026/01/proof.jpg", b"DATA")
        assert (tmp_path / "uploads" / "2026" / "01" / "proof.jpg").exists()

    def test_get_url_format(self, tmp_path):
        backend = _local(tmp_path)
        assert backend.get_url("abc.jpg") == "/delivery/proof/abc.jpg"

    def test_get_file_path_existing(self, tmp_path):
        backend = _local(tmp_path)
        backend.upload("img.jpg", b"data")
        path = backend.get_file_path("img.jpg")
        assert path is not None
        assert path.endswith("img.jpg")

    def test_get_file_path_missing_returns_none(self, tmp_path):
        backend = _local(tmp_path)
        assert backend.get_file_path("missing.jpg") is None

    def test_list_files_empty_dir(self, tmp_path):
        backend = _local(tmp_path)
        assert backend.list_files() == []

    def test_list_files_returns_timestamped_images(self, tmp_path):
        backend = _local(tmp_path)
        fname = "PKG-D001-1770914907-5763_D001.jpg"
        (tmp_path / "uploads" / fname).write_bytes(b"x")
        results = backend.list_files()
        assert len(results) == 1
        assert results[0]["key"] == fname

    def test_list_files_skips_non_image_files(self, tmp_path):
        backend = _local(tmp_path)
        (tmp_path / "uploads" / "notes.txt").write_text("ignored")
        assert backend.list_files() == []

    def test_list_files_nonexistent_base_dir_returns_empty(self):
        backend = LocalStorageBackend.__new__(LocalStorageBackend)
        backend.base_dir = r"C:\nonexistent\path\xyz999abc"
        assert backend.list_files() == []

    def test_production_guard_raises(self):
        with patch("src.backend.services.storage.settings") as s:
            s.ENV = "production"
            with pytest.raises(RuntimeError, match="not allowed in production"):
                LocalStorageBackend(r"C:\tmp\uploads")


# ─── S3StorageBackend ───────────────────────────────────────────────────────

class TestS3StorageBackend:
    def test_upload_calls_put_object(self):
        backend = _s3_backend()
        backend.client.put_object = MagicMock()
        key = backend.upload("proof/abc.jpg", b"DATA", content_type="image/jpeg")
        assert key == "proof/abc.jpg"
        backend.client.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="proof/abc.jpg",
            Body=b"DATA",
            ContentType="image/jpeg",
        )

    def test_get_url_returns_presigned_url(self):
        backend = _s3_backend()
        backend.client.generate_presigned_url = MagicMock(
            return_value="https://s3.example.com/presigned"
        )
        url = backend.get_url("proof/abc.jpg")
        assert url == "https://s3.example.com/presigned"
        backend.client.generate_presigned_url.assert_called_once()

    def test_list_files_returns_image_objects(self):
        backend = _s3_backend()
        backend.client.list_objects_v2 = MagicMock(return_value={
            "Contents": [
                {"Key": "proof.jpg", "Size": 1024, "LastModified": datetime(2026, 1, 1)},
                {"Key": "receipt.pdf", "Size": 512, "LastModified": datetime(2026, 1, 2)},
            ]
        })
        results = backend.list_files()
        assert len(results) == 1
        assert results[0]["key"] == "proof.jpg"

    def test_list_files_empty_contents_returns_empty(self):
        backend = _s3_backend()
        backend.client.list_objects_v2 = MagicMock(return_value={})
        assert backend.list_files() == []

    def test_list_files_exception_returns_empty(self):
        backend = _s3_backend()
        backend.client.list_objects_v2 = MagicMock(side_effect=Exception("S3 down"))
        assert backend.list_files() == []

    def test_ensure_bucket_creates_missing_bucket(self):
        mock_boto3, mock_client = _make_mock_boto3(head_raises=True)
        mock_client.create_bucket.return_value = {}
        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            with patch("src.backend.services.storage.settings") as s:
                s.AWS_ACCESS_KEY_ID = "KEY"
                s.AWS_SECRET_ACCESS_KEY = "SECRET"
                s.AWS_REGION = "us-east-1"
                s.S3_ENDPOINT_URL = None
                s.S3_BUCKET_NAME = "new-bucket"
                from src.backend.services.storage import S3StorageBackend
                S3StorageBackend()
        mock_client.create_bucket.assert_called_once_with(Bucket="new-bucket")

    def test_ensure_bucket_silences_create_failure(self):
        mock_boto3, mock_client = _make_mock_boto3(head_raises=True, create_raises=True)
        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            with patch("src.backend.services.storage.settings") as s:
                s.AWS_ACCESS_KEY_ID = "KEY"
                s.AWS_SECRET_ACCESS_KEY = "SECRET"
                s.AWS_REGION = "us-east-1"
                s.S3_ENDPOINT_URL = None
                s.S3_BUCKET_NAME = "locked"
                from src.backend.services.storage import S3StorageBackend
                S3StorageBackend()  # must not raise

    def test_endpoint_url_passed_to_boto3(self):
        mock_boto3, mock_client = _make_mock_boto3()
        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            with patch("src.backend.services.storage.settings") as s:
                s.AWS_ACCESS_KEY_ID = "KEY"
                s.AWS_SECRET_ACCESS_KEY = "SECRET"
                s.AWS_REGION = "us-east-1"
                s.S3_ENDPOINT_URL = "http://localhost:4566"
                s.S3_BUCKET_NAME = "test-bucket"
                from src.backend.services.storage import S3StorageBackend
                S3StorageBackend()
        call_kwargs = mock_boto3.client.call_args[1]
        assert call_kwargs.get("endpoint_url") == "http://localhost:4566"


# ─── get_storage_backend() ──────────────────────────────────────────────────

class TestGetStorageBackend:
    def test_s3_when_configured(self):
        mock_boto3, mock_client = _make_mock_boto3()
        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            with patch("src.backend.services.storage.settings") as s:
                s.PROOF_STORAGE = "s3"
                s.AWS_ACCESS_KEY_ID = "KEY"
                s.AWS_SECRET_ACCESS_KEY = "SECRET"
                s.AWS_REGION = "us-east-1"
                s.S3_ENDPOINT_URL = None
                s.S3_BUCKET_NAME = "my-bucket"
                from src.backend.services.storage import get_storage_backend, S3StorageBackend
                backend = get_storage_backend()
        assert isinstance(backend, S3StorageBackend)

    def test_local_when_proof_storage_local(self, tmp_path):
        with patch("src.backend.services.storage.settings") as s:
            s.PROOF_STORAGE = "local"
            s.AWS_ACCESS_KEY_ID = None
            s.ENV = "development"
            with patch(
                "src.backend.services.storage._get_proofs_base_dir",
                return_value=str(tmp_path),
            ):
                from src.backend.services.storage import get_storage_backend
                backend = get_storage_backend()
        assert isinstance(backend, LocalStorageBackend)

    def test_production_local_raises(self):
        with patch("src.backend.services.storage.settings") as s:
            s.PROOF_STORAGE = "local"
            s.AWS_ACCESS_KEY_ID = None
            s.ENV = "production"
            with pytest.raises(RuntimeError, match="Fatal Configuration Error"):
                from src.backend.services.storage import get_storage_backend
                get_storage_backend()
