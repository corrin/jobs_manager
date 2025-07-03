from apps.workflow.models import AIProvider

# Get all AI providers
all_providers = AIProvider.objects.all()
print("All AI Providers:")
for provider in all_providers:
    print(f"ID: {provider.id}, Name: {provider.name}, Type: {provider.provider_type}, Default: {provider.default}")

# Get a specific AI provider by type (e.g., 'Claude' or 'Gemini')
# Replace 'Claude' with the actual provider_type you are looking for
claude_provider = AIProvider.objects.filter(provider_type='Claude').first()
if claude_provider:
    print("\nClaude AI Provider Details:")
    print(f"ID: {claude_provider.id}, Name: {claude_provider.name}, Type: {claude_provider.provider_type}, Default: {claude_provider.default}")
else:
    print("\nNo Claude AI provider found.")

# You can also check for 'Gemini' or other types
gemini_provider = AIProvider.objects.filter(provider_type='Gemini').first()
if gemini_provider:
    print("\nGemini AI Provider Details:")
    print(f"ID: {gemini_provider.id}, Name: {gemini_provider.name}, Type: {gemini_provider.provider_type}, Default: {gemini_provider.default}")
else:
    print("\nNo Gemini AI provider found.")
