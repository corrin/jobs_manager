"""
Management command to import Dropbox Health & Safety documents into ProcessDocument records.

Walks a folder structure finding .doc and .docx files with Doc.NNN naming convention,
optionally uploads each to Google Drive (converting to Google Docs format), and creates
ProcessDocument records with appropriate type, tags, and metadata.
"""

import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.job.models import ProcessDocument
from apps.workflow.models import CompanyDefaults
from apps.workflow.services.error_persistence import persist_app_error

# Maps individual doc numbers to (document_type, tags, is_template)
DOC_MAPPING = {
    # Policies (procedures with policy tag)
    "100": ("procedure", ["safety", "policy"], False),
    "101": ("procedure", ["safety", "policy"], False),
    # Planning/reference docs
    "102": ("reference", ["safety", "planning"], False),
    "103": ("reference", ["safety", "planning"], False),
    "104": ("reference", ["safety", "planning"], False),
    "105": ("reference", ["safety", "planning"], False),
    "106": ("reference", ["safety", "planning"], False),
    # Inspection forms (templates)
    "107": ("form", ["safety", "inspection"], True),
    "108": ("form", ["safety", "inspection"], True),
    "110": ("form", ["safety", "inspection"], True),
    "111": ("form", ["safety", "inspection"], True),
    "112": ("register", ["safety", "ppe"], False),
    "113": ("form", ["safety", "inspection"], True),
    "114": ("form", ["safety", "inspection"], True),
    "115": ("form", ["safety", "hazard-id"], True),
    "116": ("form", ["safety", "hazard-id"], True),
    "117": ("reference", ["safety", "maintenance"], False),
    "118": ("procedure", ["safety", "lockout"], False),
    "119": ("form", ["safety", "inspection"], True),
    "120": ("form", ["training", "induction"], True),
    # Machine inspection (150-series)
    "151": ("form", ["safety", "inspection", "machinery"], True),
    "153": ("form", ["safety", "inspection", "machinery"], True),
    "168": ("form", ["safety", "inspection", "machinery"], True),
    "172": ("form", ["safety", "inspection", "machinery"], True),
    "173": ("register", ["safety", "inspection", "machinery"], False),
    # Incident management (200-series)
    "202": ("form", ["safety", "incident"], True),
    "203": ("procedure", ["safety", "incident"], False),
    "204": ("procedure", ["safety", "incident"], False),
    "205": ("form", ["safety", "incident"], True),
    "206": ("procedure", ["safety", "incident"], False),
    # Training (250-series)
    "250": ("reference", ["training"], False),
    "251": ("form", ["training", "induction"], True),
    "252": ("form", ["training", "refresher"], True),
    "253": ("form", ["training", "induction"], True),
    "255": ("form", ["training", "induction"], True),
    "256": ("form", ["training", "refresher", "machinery"], True),
    "257": ("form", ["training", "refresher", "handtool"], True),
    "258": ("form", ["training", "refresher", "lockout"], True),
    "259": ("form", ["training", "induction"], True),
    # Hand tool SOPs (300-series)
    "300": ("procedure", ["safety", "sop", "handtool"], False),
    "301": ("procedure", ["safety", "sop", "handtool"], False),
    "302": ("procedure", ["safety", "sop", "handtool"], False),
    "303": ("procedure", ["safety", "sop", "handtool"], False),
    "304": ("procedure", ["safety", "sop", "handtool"], False),
    "305": ("procedure", ["safety", "sop", "handtool"], False),
    "306": ("procedure", ["safety", "sop", "handtool"], False),
    "307": ("procedure", ["safety", "sop", "handtool"], False),
    "308": ("procedure", ["safety", "sop", "handtool"], False),
    "309": ("procedure", ["safety", "sop", "handtool"], False),
    "310": ("procedure", ["safety", "sop", "handtool"], False),
    # Machinery SOPs (350-series)
    "350": ("procedure", ["safety", "sop", "machinery"], False),
    "351": ("procedure", ["safety", "sop", "machinery"], False),
    "352": ("procedure", ["safety", "sop", "machinery"], False),
    "353": ("procedure", ["safety", "sop", "machinery"], False),
    "354": ("procedure", ["safety", "sop", "machinery"], False),
    "355": ("procedure", ["safety", "sop", "machinery"], False),
    "357": ("procedure", ["safety", "sop", "machinery"], False),
    "359": ("procedure", ["safety", "sop", "machinery"], False),
    "360": ("procedure", ["safety", "sop", "machinery"], False),
    "361": ("procedure", ["safety", "sop", "machinery"], False),
    "362": ("procedure", ["safety", "sop", "machinery"], False),
    "363": ("procedure", ["safety", "sop", "machinery"], False),
    "364": ("procedure", ["safety", "sop", "machinery"], False),
    "366": ("procedure", ["safety", "sop", "machinery"], False),
    "369": ("procedure", ["safety", "sop", "machinery"], False),
    "370": ("procedure", ["safety", "sop", "machinery"], False),
    "372": ("procedure", ["safety", "sop", "machinery"], False),
    "373": ("procedure", ["safety", "sop", "machinery"], False),
    "374": ("procedure", ["safety", "sop", "machinery"], False),
    "375": ("procedure", ["safety", "sop", "machinery"], False),
    # Registers
    "380": ("register", ["safety", "hazard"], False),
    # Emergency/general (400-series)
    "400": ("form", ["safety", "jsa"], True),
    "401": ("procedure", ["safety", "emergency"], False),
    "402": ("reference", ["safety", "sop"], False),
    "403": ("register", ["safety", "chemical"], False),
    "404": ("form", ["safety", "emergency"], True),
    "405": ("procedure", ["safety", "emergency"], False),
    # Meeting forms (415-420)
    "415": ("form", ["administration", "meeting"], True),
    "416": ("form", ["administration", "meeting"], True),
    "417": ("form", ["administration", "meeting"], True),
    "420": ("form", ["administration", "meeting"], True),
    # Air compressor
    "450": ("procedure", ["safety", "sop", "machinery"], False),
}

# Regex to extract doc number from filenames like "Doc.350", "Doc 350", "Doc.350a"
DOC_NUMBER_RE = re.compile(r"Doc\.?\s*(\d+[ab]?)", re.IGNORECASE)

# Folder names to skip entirely
SKIP_FOLDERS = {"zMSM Old Docs", "zPauls Folder", "Archive"}


def _should_skip_folder(folder_name: str) -> bool:
    """Return True if this folder should be excluded from scanning."""
    if folder_name in SKIP_FOLDERS:
        return True
    if folder_name.startswith("z"):
        return True
    return False


def _extract_doc_info(filename: str) -> tuple:
    """
    Extract doc number and title from a filename.

    Returns:
        (doc_number, title) or (None, None) if no match.
    """
    match = DOC_NUMBER_RE.search(filename)
    if not match:
        return None, None

    doc_number = match.group(1)

    # Extract title: everything after the doc number pattern, minus the extension
    stem = Path(filename).stem
    # Find where the doc number pattern ends in the stem
    title_start = match.end()
    # Adjust for the stem (no extension)
    if title_start <= len(stem):
        title = stem[title_start:].strip()
        # Clean up common prefixes/separators
        title = title.lstrip(".-_ ")
    else:
        title = stem

    if not title:
        title = f"Document {doc_number}"

    return doc_number, title


class Command(BaseCommand):
    help = "Import Dropbox Health & Safety documents into ProcessDocument records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--folder",
            required=True,
            help="Path to the H&S folder (e.g. 'dropbox/Health & Safety')",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview without uploading or creating records",
        )
        parser.add_argument(
            "--skip-upload",
            action="store_true",
            help="Create records with empty google_doc fields (for testing)",
        )
        parser.add_argument(
            "--credentials",
            help="Path to Google service account JSON key file (overrides default)",
        )
        parser.add_argument(
            "--impersonate",
            help="Email address to impersonate via domain-wide delegation "
            "(e.g. office@morrissheetmetal.co.nz)",
        )

    def handle(self, *args, **options):
        folder_path = Path(options["folder"])
        dry_run = options["dry_run"]
        skip_upload = options["skip_upload"]
        self._credentials_file = options.get("credentials")
        self._impersonate_email = options.get("impersonate")

        if not folder_path.exists():
            raise CommandError(f"Folder does not exist: {folder_path}")
        if not folder_path.is_dir():
            raise CommandError(f"Path is not a directory: {folder_path}")

        # Gather company name for records
        if not dry_run:
            company = CompanyDefaults.get_instance()
            company_name = company.company_name
        else:
            company_name = "Morris Sheetmetal"

        # Phase 1: discover all candidate files
        candidates = self._discover_files(folder_path)

        # Phase 2: resolve duplicates (prefer .doc over .docx for same doc number)
        resolved = self._resolve_duplicates(candidates)

        # Phase 3: filter out already-imported documents
        existing_numbers = set(
            ProcessDocument.objects.filter(
                document_number__in=list(resolved.keys())
            ).values_list("document_number", flat=True)
        )

        imported_count = 0
        skipped_existing = 0
        skipped_no_mapping = 0

        for doc_number in sorted(resolved.keys(), key=lambda x: x.zfill(5)):
            file_path, title = resolved[doc_number]

            if doc_number in existing_numbers:
                skipped_existing += 1
                self.stdout.write(
                    f'  Skipped Doc.{doc_number} "{title}" (already exists)'
                )
                continue

            if doc_number not in DOC_MAPPING:
                skipped_no_mapping += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  Skipped Doc.{doc_number} "{title}" (no mapping)'
                    )
                )
                continue

            doc_type, tags, is_template = DOC_MAPPING[doc_number]

            if dry_run:
                self.stdout.write(
                    f'[DRY RUN] Doc.{doc_number} "{title}" ' f"-> {doc_type} {tags}"
                )
                imported_count += 1
                continue

            # Upload to Google Drive (unless --skip-upload)
            google_doc_id = ""
            google_doc_url = ""

            if not skip_upload:
                try:
                    google_doc_id, google_doc_url = self._upload_to_google_docs(
                        file_path, f"Doc.{doc_number} {title}"
                    )
                except Exception as exc:
                    persist_app_error(exc)
                    self.stderr.write(
                        self.style.ERROR(
                            f'  FAILED to upload Doc.{doc_number} "{title}": {exc}'
                        )
                    )
                    continue

            # Create ProcessDocument record
            try:
                ProcessDocument.objects.create(
                    document_type=doc_type,
                    tags=tags,
                    is_template=is_template,
                    status="active",
                    document_number=doc_number,
                    title=title,
                    company_name=company_name,
                    site_location="",
                    google_doc_id=google_doc_id,
                    google_doc_url=google_doc_url,
                )
            except Exception as exc:
                persist_app_error(exc)
                self.stderr.write(
                    self.style.ERROR(
                        f"  FAILED to create record for Doc.{doc_number} "
                        f'"{title}": {exc}'
                    )
                )
                continue

            url_suffix = f" ({google_doc_url})" if google_doc_url else ""
            self.stdout.write(
                self.style.SUCCESS(
                    f'Imported Doc.{doc_number} "{title}" '
                    f"-> {doc_type} {tags}{url_suffix}"
                )
            )
            imported_count += 1

        # Summary
        self.stdout.write("")
        action = "Would import" if dry_run else "Imported"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {imported_count} documents, "
                f"skipped {skipped_existing} (already exist), "
                f"skipped {skipped_no_mapping} (no mapping)"
            )
        )

    def _discover_files(self, folder_path: Path) -> dict:
        """
        Walk folder recursively finding .doc/.docx files with Doc.NNN pattern.

        Returns:
            dict mapping doc_number -> list of (file_path, title) tuples
        """
        candidates = {}

        for file_path in folder_path.rglob("*"):
            # Skip non-files
            if not file_path.is_file():
                continue

            # Skip .lnk files (Windows shortcuts)
            if file_path.suffix.lower() == ".lnk":
                continue

            # Skip non-doc files
            if file_path.suffix.lower() not in (".doc", ".docx"):
                continue

            # Check if any parent folder should be skipped
            if self._is_in_skip_folder(file_path, folder_path):
                continue

            doc_number, title = _extract_doc_info(file_path.name)
            if not doc_number:
                continue

            if doc_number not in candidates:
                candidates[doc_number] = []
            candidates[doc_number].append((file_path, title))

        return candidates

    def _is_in_skip_folder(self, file_path: Path, root: Path) -> bool:
        """Check if file is inside a folder that should be skipped."""
        relative = file_path.relative_to(root)
        for part in relative.parts[:-1]:  # Check all parent folder names, not the file
            if _should_skip_folder(part):
                return True
        return False

    def _resolve_duplicates(self, candidates: dict) -> dict:
        """
        Resolve duplicate doc numbers: prefer .doc over .docx.

        Returns:
            dict mapping doc_number -> (file_path, title)
        """
        resolved = {}

        for doc_number, file_list in candidates.items():
            if len(file_list) == 1:
                resolved[doc_number] = file_list[0]
                continue

            # Prefer .doc over .docx
            doc_files = [f for f in file_list if f[0].suffix.lower() == ".doc"]
            docx_files = [f for f in file_list if f[0].suffix.lower() == ".docx"]

            if doc_files:
                # If multiple .doc files, pick the one with the latest mtime
                best = max(doc_files, key=lambda f: f[0].stat().st_mtime)
            elif docx_files:
                best = max(docx_files, key=lambda f: f[0].stat().st_mtime)
            else:
                best = file_list[0]

            resolved[doc_number] = best

        return resolved

    def _get_drive_service(self):
        """Get a Google Drive service, optionally with custom credentials."""
        if self._credentials_file:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            scopes = [
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/documents",
            ]
            creds = service_account.Credentials.from_service_account_file(
                self._credentials_file, scopes=scopes
            )
            if self._impersonate_email:
                creds = creds.with_subject(self._impersonate_email)
            return build("drive", "v3", credentials=creds, cache_discovery=False)

        from apps.job.importers.google_sheets import _svc

        return _svc("drive", "v3")

    def _upload_to_google_docs(self, file_path: Path, title: str) -> tuple:
        """
        Upload a .doc/.docx file to Google Drive, converting to Google Docs format.

        Returns:
            (doc_id, edit_url)
        """
        from googleapiclient.http import MediaFileUpload

        from apps.job.importers.google_sheets import _set_public_edit_permissions
        from apps.job.services.google_docs_service import GoogleDocsService

        drive_service = self._get_drive_service()

        ext = file_path.suffix.lower()
        mime_types = {
            ".docx": (
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"
            ),
            ".doc": "application/msword",
        }
        mime_type = mime_types.get(ext, "application/octet-stream")

        media = MediaFileUpload(str(file_path), mimetype=mime_type)
        file_metadata = {
            "name": title,
            "mimeType": "application/vnd.google-apps.document",
        }

        uploaded = (
            drive_service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id",
            )
            .execute()
        )

        doc_id = uploaded["id"]
        docs_service = GoogleDocsService()
        docs_service._move_to_safety_folder(doc_id)
        _set_public_edit_permissions(doc_id)

        edit_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        return doc_id, edit_url
