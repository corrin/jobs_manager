# workflow/services/xero_sync_service.py

import logging
import threading
import uuid

from django.core.cache import cache
from django.utils import timezone

from apps.workflow.api.xero.sync import synchronise_xero_data
from apps.workflow.api.xero.xero import get_valid_token

logger = logging.getLogger("xero")


class XeroSyncService:
    """
    Service to handle Xero synchronization as a background process.
    Ensures only one sync runs at a time via a cache-based lock.
    """

    LOCK_TIMEOUT = 60 * 60 * 4  # 4 hours
    SYNC_STATUS_KEY = "xero_sync_status"

    @staticmethod
    def start_sync():
        """
        Start a new Xero sync directly.
        Returns a tuple of (task_id, is_new) where:
        - task_id: The ID of the sync task or None if failed to start
        - is_new: True if a new sync was started, False if one was already running
        """
        task_id = str(uuid.uuid4())
        # Atomic lock acquire and store task ID
        got_lock = cache.add(
            XeroSyncService.SYNC_STATUS_KEY,
            task_id,
            timeout=XeroSyncService.LOCK_TIMEOUT,
        )

        if not got_lock:
            logger.info("Sync already running; not starting a new one")
            # Retrieve the task ID of the currently running sync
            active_task_id = cache.get(XeroSyncService.SYNC_STATUS_KEY)
            return active_task_id, False

        # Validate token
        token = get_valid_token()
        if not token:
            logger.error("No valid Xero token found")
            cache.delete(
                XeroSyncService.SYNC_STATUS_KEY
            )  # Release lock if token is invalid
            return None, False

        # Prepare task (message and progress keys still use task_id)
        cache.set(f"xero_sync_messages_{task_id}", [], timeout=86400)
        cache.set(f"xero_sync_current_entity_{task_id}", None, timeout=86400)
        cache.set(f"xero_sync_entity_progress_{task_id}", 0.0, timeout=86400)

        # Launch
        thread = threading.Thread(
            target=XeroSyncService.run_sync, args=[task_id], daemon=True
        )
        thread.start()

        logger.info(f"Started Xero sync with task ID {task_id}")
        return task_id, True

    @staticmethod
    def run_sync(task_id):
        """
        Execute the Xero sync process and store progress messages.
        Releases lock on completion.
        """
        messages_key = f"xero_sync_messages_{task_id}"
        current_key = f"xero_sync_current_entity_{task_id}"
        progress_key = f"xero_sync_entity_progress_{task_id}"

        try:
            msgs = cache.get(messages_key, [])
            for message in synchronise_xero_data():
                message["task_id"] = task_id

                # Track entity/progress
                entity = message.get("entity")
                if entity and entity != "sync":
                    cache.set(current_key, entity, timeout=86400)
                    if message.get("progress") is not None:
                        cache.set(progress_key,
                                  message["progress"], timeout=86400)

                msgs.append(message)
                cache.set(messages_key, msgs, timeout=86400)

            # Final marker
            msgs.append(
                {
                    "datetime": timezone.now().isoformat(),
                    "entity": "sync",
                    "severity": "info",
                    "message": "Sync stream ended",
                    "progress": 1.0,
                    "task_id": task_id,
                }
            )
            cache.set(messages_key, msgs, timeout=86400)
            logger.info(f"Completed Xero sync task {task_id}")

        except Exception as e:
            logger.error(
                f"Error during Xero sync task {task_id}: {e}", exc_info=True)
            msgs = cache.get(messages_key, [])
            msgs.append(
                {
                    "datetime": timezone.now().isoformat(),
                    "entity": "sync",
                    "severity": "error",
                    "message": f"Error during sync: {e}",
                    "progress": None,
                    "task_id": task_id,
                }
            )
            msgs.append(
                {
                    "datetime": timezone.now().isoformat(),
                    "entity": "sync",
                    "severity": "info",
                    "message": "Sync stream ended",
                    "progress": None,
                    "task_id": task_id,
                }
            )
            cache.set(messages_key, msgs, timeout=86400)
            # Re-raise the exception to ensure the calling process is aware of the failure
            # We are about to crash, so we need to clean up the lock
            cache.delete(current_key)
            cache.delete(progress_key)
            cache.delete(
                XeroSyncService.SYNC_STATUS_KEY
            )  # Release lock and clear task ID
            raise e

        finally:
            cache.delete(current_key)
            cache.delete(progress_key)
            cache.delete(
                XeroSyncService.SYNC_STATUS_KEY
            )  # Release lock and clear task ID

    @staticmethod
    def get_messages(task_id, since_index=0):
        msgs = cache.get(f"xero_sync_messages_{task_id}", [])
        return msgs[since_index:] if since_index < len(msgs) else []

    @staticmethod
    def get_current_entity(task_id):
        return cache.get(f"xero_sync_current_entity_{task_id}")

    @staticmethod
    def get_entity_progress(task_id):
        return cache.get(f"xero_sync_entity_progress_{task_id}", 0.0)

    @staticmethod
    def get_active_task_id():
        return cache.get(
            XeroSyncService.SYNC_STATUS_KEY
        )  # Retrieve active task ID directly from the status key
