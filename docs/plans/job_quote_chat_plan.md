# Backend Requirements: Quote Chat History API

## Overview
The frontend Vue.js app needs Django REST API endpoints to store and retrieve chat conversations for the interactive quoting feature. Each job can have an associated chat conversation where users interact with an LLM to generate quotes.

## Database Model Requirements

### JobQuoteChat Model
Create a new model to store chat messages linked to jobs:

```python
class JobQuoteChat(models.Model):
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='quote_chat_messages')
    message_id = models.CharField(max_length=100, unique=True)  # Frontend-generated unique ID
    role = models.CharField(max_length=20, choices=[('user', 'User'), ('assistant', 'Assistant')])
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)  # For extra data like streaming status, etc.
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['job', 'timestamp']),
        ]
```

## API Endpoints Required

### 1. Get Chat History
**Endpoint**: `GET /api/jobs/{job_id}/quote-chat/`

**Purpose**: Load all chat messages for a specific job

**Response**:
```json
{
  "success": true,
  "data": {
    "job_id": "uuid",
    "messages": [
      {
        "message_id": "user-1234567890",
        "role": "user",
        "content": "3 stainless steel boxes, 700x700x400mm",
        "timestamp": "2024-01-15T10:30:00Z",
        "metadata": {}
      },
      {
        "message_id": "assistant-1234567891", 
        "role": "assistant",
        "content": "I understand you need 3 stainless steel boxes...",
        "timestamp": "2024-01-15T10:30:05Z",
        "metadata": {"processing_time": 2.5}
      }
    ]
  }
}
```

### 2. Save New Message
**Endpoint**: `POST /api/jobs/{job_id}/quote-chat/`

**Purpose**: Save a new chat message (user or assistant)

**Request Body**:
```json
{
  "message_id": "user-1234567892",
  "role": "user",
  "content": "Actually, make that 5 boxes instead",
  "metadata": {}
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "message_id": "user-1234567892",
    "timestamp": "2024-01-15T10:32:00Z"
  }
}
```

### 3. Clear Chat History  
**Endpoint**: `DELETE /api/jobs/{job_id}/quote-chat/`

**Purpose**: Delete all chat messages for a job (start fresh)

**Response**:
```json
{
  "success": true,
  "data": {
    "deleted_count": 15
  }
}
```

### 4. Update Message (Optional)
**Endpoint**: `PATCH /api/jobs/{job_id}/quote-chat/{message_id}/`

**Purpose**: Update an existing message (useful for streaming responses)

**Request Body**:
```json
{
  "content": "Updated message content",
  "metadata": {"final": true}
}
```

## Authentication & Permissions
- Use existing job-level permissions
- Users can only access chat for jobs they have permission to view
- Follow existing authentication patterns in the codebase

## Error Handling
Follow existing API error response patterns:

```json
{
  "success": false,
  "error": "Job not found",
  "code": "JOB_NOT_FOUND"
}
```

## Additional Considerations

### Performance
- Index on `(job, timestamp)` for efficient message retrieval
- Consider pagination if conversations become very long

### Data Retention
- Chat messages should be preserved when jobs are archived
- Consider adding soft delete functionality

### Integration Points
- Chat history should be included in job export functionality
- Consider adding chat summary to job overview pages

## Frontend Usage
The Vue.js frontend will:
1. Load chat history when opening the quote chat interface
2. Save each message (user and assistant) as they're sent
3. Support clearing chat history with user confirmation
4. Handle streaming assistant responses by updating messages

## Testing Requirements
- Unit tests for the model
- API endpoint tests with various scenarios
- Performance tests with large conversation histories
- Permission tests to ensure proper access control