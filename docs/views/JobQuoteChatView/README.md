# Job Quote Chat Views Documentation

## Business Purpose
Provides chat conversation management for job quotation processes in jobbing shop operations. Handles AI-powered quote discussions, conversation history, and iterative quote refinements. Essential for capturing customer requirements, managing quote conversations, and maintaining audit trails of quotation discussions throughout the sales process.

## Views

### BaseJobQuoteChatView
**File**: `apps/job/views/job_quote_chat_views.py`
**Type**: Base class for chat operations

#### What it does
- Provides foundation for job quote chat REST operations
- Implements common error handling and job validation patterns
- Manages CSRF exemption for API endpoints
- Centralizes chat-specific utility methods and error responses
- Supports modern match-case error handling patterns

#### Integration
- CSRF exemption for API integration
- Standardized error response formats
- Job and message validation utilities
- Exception handling with detailed error codes

### JobQuoteChatHistoryView
**File**: `apps/job/views/job_quote_chat_views.py`
**Type**: Class-based view (APIView)
**URL**: `/api/jobs/<uuid:job_id>/quote-chat/`

#### What it does
- Manages complete chat conversation history for specific jobs
- Handles loading, saving, and clearing of chat messages
- Supports AI assistant and user message storage
- Enables iterative quote refinement conversations
- Maintains chronological message ordering for context

#### Methods and Operations

### get (Load Chat History)
**Type**: GET method within JobQuoteChatHistoryView

#### What it does
- Retrieves complete chat message history for specific job
- Returns chronologically ordered conversation data
- Formats messages for API consumption
- Supports chat session restoration and context loading

#### Parameters
- `job_id`: UUID of job to load chat history for (path parameter)

#### Returns
- **200 OK**: Chat history with formatted messages
  - `success`: True
  - `data`: Object containing job_id and messages array
  - `messages`: Array of formatted chat messages with metadata
- **404 Not Found**: Job not found
- **500 Internal Server Error**: System failures

#### Integration
- JobQuoteChat model for message persistence
- JobLookupMixin for job validation
- Timestamp formatting for API consistency
- Message metadata preservation

### post (Save New Message)
**Type**: POST method within JobQuoteChatHistoryView

#### What it does
- Saves new chat messages from users or AI assistants
- Creates message records with job relationships
- Validates message data and formats
- Supports conversation continuation and context building

#### Parameters
- `job_id`: UUID of job for message association (path parameter)
- JSON body with message data:
  - `message_id`: Unique message identifier (required)
  - `role`: Message role - "user" or "assistant" (required)
  - `content`: Message content text (required)
  - `metadata`: Optional metadata object

#### Returns
- **201 Created**: Message successfully saved
  - `success`: True
  - `data`: Object with message_id and timestamp
- **400 Bad Request**: Validation errors or invalid data
- **404 Not Found**: Job not found

#### Integration
- JobQuoteChatSerializer for data validation
- Message-job relationship creation
- Timestamp generation for chronological ordering

### delete (Clear Chat History)
**Type**: DELETE method within JobQuoteChatHistoryView

#### What it does
- Clears all chat messages for specific job
- Enables fresh conversation starts
- Provides conversation reset functionality
- Maintains audit trail of deletion operations

#### Parameters
- `job_id`: UUID of job to clear chat history for (path parameter)

#### Returns
- **200 OK**: Chat history successfully cleared
  - `success`: True
  - `data`: Object with deleted_count
- **404 Not Found**: Job not found

#### Integration
- Bulk message deletion for job
- Deletion count tracking for audit
- Safe cleanup of conversation data

### JobQuoteChatMessageView
**File**: `apps/job/views/job_quote_chat_views.py`
**Type**: Class-based view (APIView)
**URL**: `/api/jobs/<uuid:job_id>/quote-chat/<str:message_id>/`

#### What it does
- Manages individual chat message updates
- Supports streaming response updates from AI assistants
- Enables message content and metadata modifications
- Handles real-time conversation updates

### patch (Update Individual Message)
**Type**: PATCH method within JobQuoteChatMessageView

#### What it does
- Updates content and metadata of existing chat messages
- Supports streaming response updates during AI generation
- Enables message finalization and status updates
- Maintains message history with update tracking

#### Parameters
- `job_id`: UUID of job containing the message (path parameter)
- `message_id`: String identifier of message to update (path parameter)
- JSON body with update data:
  - `content`: Updated message content (optional)
  - `metadata`: Updated metadata object (optional)

#### Returns
- **200 OK**: Message successfully updated
  - `success`: True
  - `data`: Updated message data with timestamp
- **400 Bad Request**: Validation errors
- **404 Not Found**: Job or message not found

#### Integration
- JobQuoteChatUpdateSerializer for partial updates
- Message lookup and validation
- Metadata update support for streaming states

### dispatch (CSRF Exemption)
**Type**: Method decorator for API compatibility

#### What it does
- Exempts chat API endpoints from CSRF validation
- Enables seamless API integration for chat functionality
- Supports modern single-page application integration
- Maintains security while enabling API access

## Error Handling
- **400 Bad Request**: Invalid message data, validation errors, or malformed requests
- **404 Not Found**: Job not found or message not found with specific error codes
- **500 Internal Server Error**: System failures with comprehensive logging
- Modern match-case error handling for precise error responses
- Detailed error codes (JOB_NOT_FOUND, MESSAGE_NOT_FOUND) for client handling
- Exception logging for debugging and monitoring

## Business Rules
- Chat messages are associated with specific jobs for context
- Messages maintain chronological ordering through timestamps
- Both user and assistant messages are supported with role identification
- Message updates support streaming AI responses
- Chat history can be cleared for fresh conversation starts
- Message IDs must be unique within job conversations

## Integration Points
- **JobQuoteChat Model**: Message persistence and job relationships
- **JobLookupMixin**: Job validation and error handling
- **JobQuoteChatSerializer**: Message validation and creation
- **JobQuoteChatUpdateSerializer**: Message update validation
- **AI Integration**: Support for assistant message streaming and updates

## Performance Considerations
- Efficient message ordering with database indexes
- Optimized job lookup with UUID-based queries
- Partial update support for streaming scenarios
- Bulk deletion operations for chat clearing
- Serializer optimization for API responses

## Security Considerations
- CSRF exemption with careful API design
- Job-based message access control
- Input validation for all message operations
- Error message sanitization to prevent information leakage
- Audit logging for conversation tracking

## AI Integration Features
- **Streaming Support**: Real-time message updates during AI generation
- **Role Management**: Clear distinction between user and assistant messages
- **Metadata Tracking**: Support for AI state and processing information
- **Context Preservation**: Complete conversation history for AI context
- **Iterative Refinement**: Multiple conversation rounds for quote development

## Related Views
- Job management views for quote context
- Quote generation views for AI integration
- Job REST views for comprehensive job management
- Quote import views for external data integration
