"""Shared test setup. Tests never call Gemini, Firecrawl or Supabase."""
import os

# Fake settings, applied before pytest imports any app module. load_dotenv() never overrides a
# variable that's already set, so these win over your real .env. If a call slips past a test's
# fake, it fails against these values instead of reaching a real service.
os.environ.update({
    "GEMINI_API_KEY": "test-gemini-key",
    "FIRECRAWL_API_KEY": "fc-test-key",
    "API_SECRET": "test-api-secret",
    "SUPABASE_URL": "https://project.supabase.test",  # .test domains never resolve
    "SUPABASE_SECRET_KEY": "test-supabase-key",
    "DATABASE_URL": "postgresql://test:test@127.0.0.1:1/test",  # port 1: nothing listens there
})
