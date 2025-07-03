# Gemini Chat Implementation Guide

This document outlines the architecture and setup process for the AI-powered quoting chatbot, which uses Google's Gemini models to provide intelligent, context-aware responses.

## 1. Overview

The Gemini chat feature provides an interactive interface where estimators can get real-time assistance for creating job quotes. The chatbot can access internal supplier pricing data, compare materials, and generate estimates by leveraging a suite of internal tools (MCP - Model Context Protocol).

The system is designed to be flexible, allowing administrators to configure different AI providers and models through a dedicated admin interface. This implementation uses the `gemini-2.5-flash-lite-preview-06-17` model by default but can be configured to use other Gemini models.

## 2. Architectural Flow

The chat system follows a clear request-response cycle that involves the frontend, backend, and the Gemini API.

1.  **User Input (Frontend)**: An estimator types a message into the `QuotingChatView` for a specific job.
2.  **API Request (Frontend -> Backend)**: The frontend sends the user's message to the Django backend via a POST request to the `/api/jobs/<job_id>/quote-chat/interaction/` endpoint.
3.  **Service Orchestration (Backend)**:
    *   The `JobQuoteChatInteractionView` receives the request.
    *   It instantiates `GeminiChatService`.
4.  **AI Provider Configuration (Backend)**:
    *   `GeminiChatService` queries the `workflow_aiprovider` table (via the `AIProvider` model) to find the default provider for `provider_type='Gemini'`.
    *   It retrieves the associated API key and configures the `google-generativeai` client.
5.  **LLM Call with Tools (Backend -> Gemini API)**:
    *   The service constructs a prompt including the user's message, conversation history, and a description of the available MCP tools.
    *   It sends the request to the Gemini API.
6.  **Tool Execution (Gemini API -> Backend -> Gemini API)**:
    *   If Gemini decides to use a tool (e.g., `search_products`), it sends a function call request back to the backend.
    *   `GeminiChatService` executes the requested MCP tool against the application's database.
    *   The result of the tool is sent back to the Gemini API in a new request.
7.  **Final Response (Gemini API -> Backend)**: Gemini processes the tool's output and generates a final, human-readable text response.
8.  **Persistence and Response (Backend -> Frontend)**:
    *   The backend saves the assistant's final message to the `job_quote_chat` table.
    *   It serializes the new message object and returns it to the frontend as the API response.
9.  **Display (Frontend)**: The `QuotingChatView` receives the assistant's message and displays it in the chat interface.

## 3. Key Components

### Backend (`jobs_manager`)

| File/Class                                      | Purpose                                                                                                                              |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `apps/job/services/gemini_chat_service.py`      | The core service that orchestrates the entire interaction with the Gemini API, including tool handling and history management.           |
| `apps/workflow/models/ai_provider.py`           | The Django model that maps to the `workflow_aiprovider` table, storing API keys, model names, and provider types.                      |
| `apps/job/views/job_quote_chat_api.py`          | Contains `JobQuoteChatInteractionView`, the API endpoint that receives chat requests from the frontend.                                |
| `apps/quoting/mcp.py`                           | Defines the `QuotingTool` and `SupplierProductQueryTool` classes, which provide the functions the Gemini model can call.               |
| `apps/job/management/commands/test_gemini_chat.py` | A Django management command for end-to-end testing of the chat service from the command line.                                          |

### Frontend (`jobs_manager_front`)

| File/Component                                | Purpose                                                                                               |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `src/views/QuotingChatView.vue`               | The main chat interface where users interact with the assistant.                                      |
| `src/services/quote-chat.service.ts`          | Contains the `getAssistantResponse` method that calls the backend's chat interaction endpoint.        |
| `src/views/AdminAIProvidersView.vue`          | The admin page for viewing, creating, editing, and deleting AI providers.                             |
| `src/components/admin/AIProviderFormModal.vue` | The modal form used to create and edit AI provider configurations. It defaults to the 'Gemini' type. |
| `src/services/aiProviderService.ts`           | The service responsible for all CRUD operations related to AI providers via the backend API.          |

## 4. Setup and Configuration

To enable the Gemini chatbot, you must configure a Gemini provider in the admin panel.

1.  **Navigate to the Admin Panel**: Log in with a superuser account and go to the **Admin** section.
2.  **Select AI Providers**: In the admin sidebar, click on **AI Providers**.
3.  **Add a New Provider**: Click the **"Add New Provider"** button.
4.  **Fill in the Form**:
    *   **Name**: Enter a descriptive name (e.g., "Default Gemini Flash").
    *   **Provider Type**: Select **"Google (Gemini)"** from the dropdown.
    *   **Model Name**: Enter the specific model you want to use. If left blank, it will default to `gemini-2.5-flash-lite-preview-06-17`.
    *   **API Key**: Paste your Google AI Studio API key.
    *   **Default**: Check this box to make this the default provider for all Gemini-based features.
5.  **Save Changes**: Click **"Save Changes"** to create the provider.

The system is now configured to use Gemini for chat responses.

## 5. Testing the Implementation

You can perform an end-to-end test using the provided management command. This is the best way to verify that your API key is correct and the service is functioning as expected.

1.  **Open your terminal**.
2.  **Navigate to the backend project directory**: `cd /path/to/corrin/jobs_manager`.
3.  **Run the test command**:
    You will need a valid `job_id` (UUID) from your database.

    ```bash
    poetry run python manage.py test_gemini_chat <your_job_id> "Your test message here"
    ```

    **Example:**
    ```bash
    poetry run python manage.py test_gemini_chat "a1b2c3d4-e5f6-7890-1234-567890abcdef" "Can you find me pricing for 2mm aluminium sheet?"
    ```

### Expected Output

If successful, you will see a detailed log of the process, followed by the AI's final response.

```
--- Starting Gemini Chat Test for Job ID: a1b2c3d4-e5f6-7890-1234-567890abcdef ---
User Message: 'Can you find me pricing for 2mm aluminium sheet?'
Checking for job a1b2c3d4-e5f6-7890-1234-567890abcdef...
Found Job: My Test Job
Initializing GeminiChatService...
Service initialized.
Sending message to AI and waiting for response...

--- AI Response Received ---
Message ID: assistant-................
Role: assistant

--- Content ---
Of course! I found the following pricing for 2mm aluminium sheet:
- Supplier A: Aluminium Sheet 2mm 2400x1200 - $150.00 per sheet
- Supplier B: Aluminium Plate 2mm 2500x1250 - $165.00 per sheet
--- End Content ---

--- Tools Used ---
Tool: get_pricing_for_material
Input: {'material_type': 'aluminium', 'dimensions': '2mm'}
---

--- Test Completed Successfully ---
```

If you encounter an error, the command will provide a descriptive message, such as an invalid API key or a misconfigured provider.
