# Lovable Integration Prompt

Build the frontend against the existing VideoSpark backend at:

- `https://video-spark.onrender.com`

This is a backend-first product. The frontend must consume the backend contracts exactly and must not recreate provider logic in the browser.

## Product scope
- Build these user-facing flows:
  - normal video render
  - image-story render
  - script helper
  - voice picker
  - caption preset picker
  - projects/history
  - live status polling
- Keep avatar hidden. `avatar-render` is disabled.
- Do not build payments, team management, article workflow, moving-image mode, music, or direct provider integrations.

## Auth
- Use Supabase Auth in the browser.
- Every protected request must send:
  - `Authorization: Bearer <supabase_access_token>`
- Never expose:
  - `SUPABASE_SERVICE_KEY`
  - `GEMINI_API_KEY`
  - `ELEVENLABS_API_KEY`
  - `OPENAI_API_KEY`

## Frontend environment
- Configure these values in Lovable:
  - `VITE_API_BASE_URL=https://video-spark.onrender.com`
  - `VITE_SUPABASE_URL=<your-supabase-url>`
  - `VITE_SUPABASE_ANON_KEY=<your-supabase-anon-key>`

## Supported backend endpoints
- `GET /health`
- `GET /api/v1/voices`
- `GET /api/v1/caption-presets`
- `POST /api/v1/generate-script`
- `POST /api/v1/render`
- `POST /api/v1/image-story-render`
- `POST /api/v1/calculate-credits`
- `GET /api/v1/status?pid=<uuid>`
- `GET /api/v1/projects`

## Required frontend behavior

### 1. Voice picker
- Load voices from `GET /api/v1/voices`.
- Show for each voice:
  - `name`
  - `language`
  - `labels`
  - `thumbnailUrl`
  - preview audio if `previewAudioUrl` exists
- The backend already marks the default voice with `isDefault`.
- When the user selects a voice, send `voice.voiceId`.
- If the user does not choose one, the backend default is allowed.

### 2. Caption preset picker
- Load presets from `GET /api/v1/caption-presets`.
- Support positions:
  - `top`
  - `middle`
  - `bottom`
- Support these preset ids:
  - `karaoke-bold`
  - `karaoke-clean`
  - `karaoke-pop`
- If captions are enabled, voice must also be enabled.

### 3. Script helper
- Add a helper flow that calls `POST /api/v1/generate-script`.
- Request body:
```json
{
  "prompt": "Create a premium short-form ad for an AI video tool.",
  "tone": "sharp, modern, persuasive",
  "targetDurationSeconds": 20,
  "language": "en"
}
```
- Render the backend response fields:
  - `title`
  - `hook`
  - `script`
  - `sceneBeats`
- Let the user edit the generated script before submitting a render.
- Do not automatically render immediately after script generation.

### 4. Normal render flow
- Use `POST /api/v1/render` for standard prompt/script video generation.
- Supported workflows:
  - `script-to-video`
  - `prompt-to-video`
- Supported media:
  - `ai-video`
- Supported output:
  - `9:16`
  - `720p`
  - `1080p`
- Do not send `projectId`.

Example:
```json
{
  "workflow": "script-to-video",
  "source": {
    "text": "Most videos fail because the idea is weak, the edit is slow, and the workflow is messy. VideoSpark helps you go from concept to polished short-form video in minutes. Create faster and publish with confidence.",
    "stylePrompt": "Cinematic startup ad, premium lighting, clean modern composition.",
    "durationSeconds": 20
  },
  "media": {
    "type": "ai-video",
    "quality": "pro",
    "density": "medium"
  },
  "voice": {
    "enabled": true,
    "voiceId": "EXAVITQu4vr4xnSDxMaL",
    "language": "en",
    "stability": 0.4
  },
  "captions": {
    "enabled": true,
    "preset": "karaoke-pop",
    "position": "middle"
  },
  "render": {
    "resolution": "720p"
  },
  "options": {
    "promptTargetDuration": 20
  },
  "aspectRatio": "9:16"
}
```

### 5. Image-story render flow
- Add a separate entry point that calls `POST /api/v1/image-story-render`.
- This is not the same as the normal render form.
- Use it for a 5-frame narrated story assembled from generated images.
- Keep the same status polling UX as normal renders.

Example:
```json
{
  "source": {
    "prompt": "Tell a five-scene story about a founder turning a raw idea into a high-converting short-form ad.",
    "stylePrompt": "Premium vertical campaign, recurring protagonist, cinematic realism, social-first framing.",
    "durationSeconds": 25
  },
  "voice": {
    "enabled": true,
    "voiceId": "EXAVITQu4vr4xnSDxMaL",
    "language": "en",
    "stability": 0.4
  },
  "captions": {
    "enabled": true,
    "preset": "karaoke-clean",
    "position": "middle"
  },
  "render": {
    "resolution": "1080p"
  },
  "options": {
    "promptTargetDuration": 25
  },
  "aspectRatio": "9:16"
}
```

### 6. Status polling
- After `POST /api/v1/render` or `POST /api/v1/image-story-render`, store the returned `pid`.
- Poll `GET /api/v1/status?pid=<uuid>` every 3 to 5 seconds.
- Stop polling on terminal states:
  - `completed`
  - `failed`
- Render these backend fields:
  - `project_status`
  - `job_status`
  - `progress`
  - `error_message`
  - `output_video_url`
  - `metadata.stageLabel`
- A render is only downloadable/playable when `output_video_url` is non-null.

### 7. Projects/history
- Use `GET /api/v1/projects` to populate the dashboard/history view.
- Show current status and final result state for each project.
- Do not build mock history entries.

## UX notes
- Show a segmented choice between:
  - `Video Render`
  - `Image Story`
- Add a script-assist button near the main prompt/script field.
- Make voice selection and caption style visible controls, not hidden defaults.
- Put the caption position control in the same section as the caption preset selector.

## Explicitly avoid
- Hardcoded fake voice lists
- Hardcoded fake status states
- Direct calls to Gemini, ElevenLabs, OpenAI Images, or Supabase service-role APIs
- Guessing storage paths or constructing output URLs manually
- Exposing inactive or disabled backend flows
- Showing avatar mode in the UI

## Acceptance criteria
- User can log in with Supabase Auth.
- User can fetch real voices and caption presets from the backend.
- User can generate a script suggestion, edit it, and submit a render.
- User can submit both a normal render and an image-story render.
- User can poll real status until `completed` or `failed`.
- A successful render must show a playable `output_video_url`.
