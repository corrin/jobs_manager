# Backend Changes for Chat File Upload

## Overview
The frontend now uploads files to jobs and stores file IDs in chat message metadata. The backend needs to extract file IDs from chat history and include those files in Gemini API calls using the File API.

## What Changed in Frontend
- Users can click paperclip icon to upload files
- Files are uploaded to the job using existing `/job/rest/jobs/{job_id}/files/` endpoint
- A chat message is created: "Uploaded: filename.pdf"
- Message metadata stores: `{"file_ids": ["uuid1", "uuid2"], "filenames": ["file1.pdf", "file2.jpg"]}`

## Implementation Details

### Files Involved

1. **New Service**: `apps/job/services/chat_file_service.py`
   - Extracts file IDs from chat message metadata
   - Fetches JobFile records
   - Uploads files to Gemini using `genai.upload_file()`

2. **Updated Service**: `apps/job/services/gemini_chat_service.py`
   - Integrates ChatFileService
   - Attaches files to messages in chat history based on metadata

### How It Works

```python
# 1. Extract file IDs from ALL messages in chat history
file_ids = ChatFileService.extract_file_ids_from_chat_history(messages)

# 2. Fetch all files once
job_files = ChatFileService.fetch_job_files(job_id, file_ids)

# 3. For each message in history that has file_ids in metadata:
for msg in messages:
    parts = [msg.content]  # Start with text

    if msg.metadata and 'file_ids' in msg.metadata:
        # Get files for THIS specific message
        message_files = [f for f in job_files if f.id in msg.metadata['file_ids']]

        # Upload each file to Gemini and get File objects
        for file in message_files:
            uploaded = genai.upload_file(
                path=file.file_path,
                mime_type=file.mime_type,
                display_name=file.filename
            )
            parts.append(uploaded)  # Gemini File object

    chat_history.append({
        "role": gemini_role,
        "parts": parts  # Text + Gemini File objects
    })
```

## Key Implementation Points

1. **File API Usage**: Files are uploaded to Gemini's File API using `genai.upload_file()`, not sent as base64 inline data
2. **Per-Message Attachment**: Files are attached to the specific message that uploaded them (via metadata.file_ids)
3. **Persistent Across Conversation**: Once uploaded, files remain in context for all subsequent turns
4. **Supported Formats**: Images (JPEG, PNG, GIF, WebP), PDFs, audio, video

## Key Points

1. **No API schema changes needed** - request body stays the same
2. **Files persist across conversation** - once uploaded, always in context
3. **Efficient** - only fetches files that were uploaded in this chat
4. **Automatic** - frontend doesn't need to track or resend file IDs

## Testing Checklist

- [ ] Upload image → ask Gemini "what's in this image?"
- [ ] Upload PDF → ask Gemini "summarize this document"
- [ ] Upload multiple files → verify all are included
- [ ] Chat without files → verify still works
- [ ] Upload file → clear chat → verify file doesn't appear in new conversation (since metadata is cleared)

## Dependencies

No new dependencies required - uses existing `google-generativeai` package.
