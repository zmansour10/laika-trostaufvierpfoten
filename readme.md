# Laika · Letter studio

A private Streamlit workspace for generating, editing, and downloading LAIKA letters. A standalone script provides the same AI generation outside the website.

## Run locally

```sh
poetry install --no-root
poetry run streamlit run main.py
```

Open `http://localhost:8501`. Configure `.env` beside `main.py` (use `.env.example` as a reference; keep existing secrets):

```dotenv
MyKey=your-key-here
GEMINI_API_KEY=your-google-ai-studio-key
# Optional, enables both OpenAI models:
OPENAI_API_KEY=your-openai-api-key
```

`MyKey` is the workspace access key; it is separate from the AI providers' API keys. Comparison is exact and case-sensitive, including spaces and line breaks. Successful validation unlocks the workspace and clears the entered key. **Lock workspace** clears the session's draft and inputs. Changing or removing `MyKey` revokes existing access on the next interaction and clears the draft. Configuration is reread without restarting. Missing API keys disable generation for that provider.

## Streamlit Community Cloud

In the app's **Settings → Secrets**, use top-level, case-sensitive TOML keys (quoted strings, without a section header):

```toml
MyKey = "your-workspace-access-key"
GEMINI_API_KEY = "your-gemini-api-key"
# Optional:
OPENAI_API_KEY = "your-openai-api-key"
```

Both workspace validation and AI generation read configuration in this order: **Streamlit Secrets → environment variables → local `.env`**. `GOOGLE_API_KEY` is also accepted for Gemini. No `.env` file is needed on the deployed app. For local Streamlit Secrets, use `.streamlit/secrets.toml`, which is ignored by Git. Never commit real credentials. See [Streamlit's secrets documentation](https://docs.streamlit.io/develop/concepts/connections/secrets-management) for the supported format and restart requirements.

## Reference library and drafting

- Put historical letters in `data/letters/` and association information in `data/website_info/`.
- Every non-empty `.txt` file, including nested folders, is read in full as UTF-8 (a UTF-8 BOM is supported). Empty files are listed as skipped. Both folders need at least one populated file.
- The prompt includes the full library, the selected purpose, audience, tone, length, language, date, and optional instructions/signatory. Association information takes precedence over historical examples. The instructions explicitly prevent carrying old anniversaries, events, deadlines, or unsupported claims into a new letter.
- Each purpose has its own subject, greeting, content, closing, and suggested audience. Donation appeals address supporters; funding enquiries address institutions; thank-you letters express gratitude without making a new financial request. Historical judicial appeals supply facts and voice, rather than dictating the new letter's objective. Custom audiences are preserved when changing purpose. The standalone CLI also resolves its default audience from `--purpose`.
- Changing settings leaves your existing draft visible with a notice until you choose **Generate a new version**. The preview identifies the purpose used for that draft. A known court-allocation subject is rejected if a model returns it for another built-in purpose.
- The workspace shows the library after unlocking. Generate a draft, review the preview, edit it, then choose **Save & prepare download**. This saves the exact edited UTF-8 text to `data/letters/` and offers **Download saved letter (.txt)** with identical content. Further edits require saving again. Generating again replaces the current draft only on success; API errors preserve it.
- Saved letters join the reference library for future generations and remain after locking or refreshing. Content-derived filenames prevent repeated saves of unchanged text from adding duplicates, and existing letters are never overwritten. Unsaved drafts remain in the Streamlit session and can be lost on refresh/reconnection. The UI does not send letters to recipients.
- For predictable context use, libraries above 300,000 characters are rejected, never silently truncated. The provider may have additional token limits.

The brief and reference texts are sent to the selected provider only when generating. No web search, grounding, file uploads, browsing, or external tools are enabled. OpenAI requests use `store=False`. Provider policies still govern their processing and retention. `.env` is ignored by Git; keys are never included in prompts or provider-error messages. The access field shows the user's own input as plain text.

## Models

| Provider | Model | API model ID | App request limit |
| --- | --- | --- | --- |
| Gemini | Gemini 3.5 Flash Lite | `gemini-3.5-flash-lite` | 15/minute |
| Gemini | Gemini 3.8 Flash | `gemini-3.8-flash` | 5/minute |
| Gemini | Gemini 3.6 Flash | `gemini-3.6-flash` | 5/minute |
| OpenAI | GPT-6 Luna | `gpt-6-luna` | Provider-managed |
| OpenAI | GPT-4o mini | `gpt-4o-mini` | Provider-managed |

The Gemini app limits follow the requested 15/5/5 RPM settings. A sliding window is shared across sessions in a single server process for each API key/model; independent processes do not share it. Google may enforce different RPM, token, or daily quotas for your account. Free-tier availability and model access depend on the account. Requests are not automatically retried and there is no automatic model/provider fallback.

Model references: [Google's model catalog](https://ai.google.dev/gemini-api/docs/models), [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [GPT-4o mini](https://developers.openai.com/api/docs/models/gpt-4o-mini), [OpenAI Responses quickstart](https://developers.openai.com/api/docs/quickstart).

## Standalone script

```sh
poetry run python generate_letter.py --model gemini-3.5-flash-lite \
  --instructions "Bitte die unbürokratische Soforthilfe hervorheben." \
  --output data/generated/new_letter.txt

poetry run python generate_letter.py --model gpt-6-luna --output data/generated/openai_letter.txt
poetry run python generate_letter.py --help
```

Use `--dry-run` to review the full prompt without contacting a provider. Optional flags include `--purpose`, `--recipient`, `--language`, `--signatory`, `--date YYYY-MM-DD`, and `--data-dir`. Without `--output`, the finished letter prints to stdout. Generated files outside the two reference folders do not enter future prompts. The standalone CLI is for the server operator and does not use the website access gate.

## Verification

```sh
poetry run python -m unittest discover -s tests -v
```

The offline checks cover full source inclusion, prompt configuration, Gemini and OpenAI request construction, disabled tools, request limits, incomplete/error responses, the access gate, key rotation, editing, downloads, and draft preservation. They do not consume API quota.
