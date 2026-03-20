from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Workflow(str, Enum):
    SCRIPT_TO_VIDEO = "script-to-video"
    PROMPT_TO_VIDEO = "prompt-to-video"
    ARTICLE_TO_VIDEO = "article-to-video"
    MUSIC_TO_VIDEO = "music-to-video"
    AVATAR_TO_VIDEO = "avatar-to-video"
    STATIC_BACKGROUND_VIDEO = "static-background-video"
    MOTION_TRANSFER = "motion-transfer"
    CAPTION_VIDEO = "caption-video"
    AD_GENERATOR = "ad-generator"


class MediaType(str, Enum):
    MOVING_IMAGE = "moving-image"
    AI_VIDEO = "ai-video"
    VIDEO = "video"
    STOCK_VIDEO = "stock-video"
    CUSTOM = "custom"


class Density(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnimationType(str, Enum):
    NONE = "none"
    SOFT = "soft"
    DYNAMIC = "dynamic"
    DEPTH = "depth"


class Quality(str, Enum):
    STANDARD = "standard"
    PRO = "pro"
    ULTRA = "ultra"


class ImageModel(str, Enum):
    CHEAP = "cheap"
    GOOD = "good"
    ULTRA = "ultra"


class VideoModel(str, Enum):
    BASE = "base"
    PRO = "pro"
    ULTRA = "ultra"
    VEO3 = "veo3"
    SORA2 = "sora2"


class AspectRatio(str, Enum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    SQUARE = "square"
    NINE_SIXTEEN = "9:16"
    SIXTEEN_NINE = "16:9"
    ONE_ONE = "1:1"
    AUTO = "auto"


class CaptionPosition(str, Enum):
    TOP = "top"
    MIDDLE = "middle"
    BOTTOM = "bottom"


class SyncTarget(str, Enum):
    BEATS = "beats"
    LYRICS = "lyrics"


class SummarizationPreference(str, Enum):
    SUMMARIZE = "summarize"
    SUMMARIZE_IF_LONG = "summarizeIfLong"
    NO_SUMMARIZATION = "no-summarization"


class RenderResolution(str, Enum):
    P720 = "720p"
    P1080 = "1080p"
    K4 = "4k"


class MediaItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: str
    type: str | None = None
    title: str | None = None
    url_low_res: str | None = Field(default=None, alias="urlLowRes")
    image_preview: str | None = Field(default=None, alias="imagePreview")
    no_reencode: bool | None = Field(default=None, alias="noReencode")


class SourceInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    text: str | None = None
    prompt: str | None = None
    style_prompt: str | None = Field(default=None, alias="stylePrompt")
    duration_seconds: float | None = Field(default=None, alias="durationSeconds")
    url: str | None = None
    recording_type: str | None = Field(default=None, alias="recordingType")
    scraping_prompt: str | None = Field(default=None, alias="scrapingPrompt")
    website_to_record: str | None = Field(default=None, alias="websiteToRecord")
    quizz_data: dict[str, Any] | None = Field(default=None, alias="quizzData")


class MediaConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: MediaType = MediaType.MOVING_IMAGE
    density: Density | None = None
    max_items: int | None = Field(default=None, alias="maxItems")
    animation: AnimationType | None = None
    quality: Quality | None = None
    image_model: ImageModel | None = Field(default=None, alias="imageModel")
    video_model: VideoModel | None = Field(default=None, alias="videoModel")
    media_preset: str | None = Field(default=None, alias="mediaPreset")
    b_roll_type: str | None = Field(default=None, alias="bRollType")
    place_avatar_in_context: bool | None = Field(default=None, alias="placeAvatarInContext")
    use_only_provided: bool | None = Field(default=None, alias="useOnlyProvided")
    provided: list[MediaItem] | None = None
    background_video: MediaItem | None = Field(default=None, alias="backgroundVideo")
    merge_videos: bool | None = Field(default=None, alias="mergeVideos")
    merge_videos_full: bool | None = Field(default=None, alias="mergeVideosFull")
    add_audio_to_videos: bool | None = Field(default=None, alias="addAudioToVideos")
    turn_images_into_videos: bool | None = Field(default=None, alias="turnImagesIntoVideos")
    apply_style_transfer: bool | None = Field(default=None, alias="applyStyleTransfer")


class VoiceConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    voice_id: str | None = Field(default=None, alias="voiceId")
    stability: float | None = None
    speed: float | None = None
    use_legacy_model: bool | None = Field(default=None, alias="useLegacyModel")
    enhance_audio: bool | None = Field(default=None, alias="enhanceAudio")
    language: str | None = None


class CaptionsConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    preset: str | None = None
    position: CaptionPosition | None = None
    auto_crop: bool | None = Field(default=None, alias="autoCrop")


class MusicConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    track_name: str | None = Field(default=None, alias="trackName")
    audio_url: str | None = Field(default=None, alias="audioUrl")
    url: str | None = None
    sound_wave: bool | None = Field(default=None, alias="soundWave")
    sync_with: SyncTarget | None = Field(default=None, alias="syncWith")
    generate_music: bool | None = Field(default=None, alias="generateMusic")
    music_generation_model: str | None = Field(default=None, alias="musicGenerationModel")
    generation_music_prompt: str | None = Field(default=None, alias="generationMusicPrompt")
    enable_lyrics_lip_sync: bool | None = Field(default=None, alias="enableLyricsLipSync")
    generate_lyrics_from_prompt: bool | None = Field(default=None, alias="generateLyricsFromPrompt")


class WatermarkConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: str | None = None
    position: str | None = None


class OptionsConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    prompt_target_duration: float | None = Field(default=None, alias="promptTargetDuration")
    target_duration: int | None = Field(default=None, alias="targetDuration")
    summarization_preference: SummarizationPreference | None = Field(
        default=None,
        alias="summarizationPreference",
    )
    output_count: int | None = Field(default=None, alias="outputCount")
    disable_audio: bool | None = Field(default=None, alias="disableAudio")
    disable_voice: bool | None = Field(default=None, alias="disableVoice")
    nsfw_filter: bool | None = Field(default=None, alias="nsfwFilter")
    add_stickers: bool | None = Field(default=None, alias="addStickers")
    sound_effects: bool | None = Field(default=None, alias="soundEffects")
    has_to_transcript: bool | None = Field(default=None, alias="hasToTranscript")
    optimized_for_chinese: bool | None = Field(default=None, alias="optimizedForChinese")
    language: str | None = None
    watermark: WatermarkConfig | None = None
    use_only_provided_media: bool | None = Field(default=None, alias="useOnlyProvidedMedia")
    character_ids: list[str] | None = Field(default=None, alias="characterIds")
    selected_characters: list[str] | None = Field(default=None, alias="selectedCharacters")
    use_whole_audio: bool | None = Field(default=None, alias="useWholeAudio")
    selected_palette: str | None = Field(default=None, alias="selectedPalette")
    make_last_slide_fill_recording_length: bool | None = Field(
        default=None,
        alias="makeLastSlideFillRecordingLength",
    )
    prevent_summarization: bool | None = Field(default=None, alias="preventSummarization")
    has_to_generate_cover: bool | None = Field(default=None, alias="hasToGenerateCover")
    cover_text_type: str | None = Field(default=None, alias="coverTextType")
    fetch_news: bool | None = Field(default=None, alias="fetchNews")
    has_text_small_at_bottom: bool | None = Field(default=None, alias="hasTextSmallAtBottom")
    custom_image_generation_rules_slug: str | None = Field(
        default=None,
        alias="customImageGenerationRulesSlug",
    )


class RenderConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    resolution: RenderResolution | None = None
    compression: float | None = None
    frame_rate: float | None = Field(default=None, alias="frameRate")


class AvatarConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    preset_id: str | None = Field(default=None, alias="presetId")
    url: str | None = None
    mime_type: str | None = Field(default=None, alias="mimeType")
    image_model: str | None = Field(default=None, alias="imageModel")
    remove_background: bool | None = Field(default=None, alias="removeBackground")


class AdvancedConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    custom_creation_params: dict[str, Any] | None = Field(default=None, alias="customCreationParams")


class RenderRequest(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    workflow: Workflow
    webhook_url: str | None = Field(default=None, alias="webhookUrl")
    project_id: str | None = Field(default=None, alias="projectId")
    source: SourceInput = Field(default_factory=SourceInput)
    media: MediaConfig = Field(default_factory=MediaConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    captions: CaptionsConfig = Field(default_factory=CaptionsConfig)
    music: MusicConfig = Field(default_factory=MusicConfig)
    options: OptionsConfig = Field(default_factory=OptionsConfig)
    render: RenderConfig = Field(default_factory=RenderConfig)
    avatar: AvatarConfig | None = None
    character_ids: list[str] | None = Field(default=None, alias="characterIds")
    metadata: dict[str, Any] | None = None
    aspect_ratio: AspectRatio | str | None = Field(default=None, alias="aspectRatio")
    advanced: AdvancedConfig | None = None

    @model_validator(mode="after")
    def validate_workflow_inputs(self) -> "RenderRequest":
        if self.workflow == Workflow.SCRIPT_TO_VIDEO and not self.source.text:
            raise ValueError("source.text is required for script-to-video.")
        if self.workflow == Workflow.PROMPT_TO_VIDEO and not self.source.prompt:
            raise ValueError("source.prompt is required for prompt-to-video.")
        if self.workflow == Workflow.ARTICLE_TO_VIDEO and not self.source.url:
            raise ValueError("source.url is required for article-to-video.")
        if self.workflow == Workflow.AVATAR_TO_VIDEO and not (self.source.text or self.source.prompt):
            raise ValueError("source.text or source.prompt is required for avatar-to-video.")
        return self


class AvatarRenderRequest(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    webhook_url: str | None = Field(default=None, alias="webhookUrl")
    source: SourceInput = Field(default_factory=SourceInput)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    captions: CaptionsConfig = Field(default_factory=CaptionsConfig)
    music: MusicConfig = Field(default_factory=MusicConfig)
    options: OptionsConfig = Field(default_factory=OptionsConfig)
    render: RenderConfig = Field(default_factory=RenderConfig)
    metadata: dict[str, Any] | None = None
    aspect_ratio: AspectRatio | str | None = Field(default=None, alias="aspectRatio")

    @model_validator(mode="after")
    def validate_inputs(self) -> "AvatarRenderRequest":
        if not (self.source.text or self.source.prompt):
            raise ValueError("source.text or source.prompt is required for avatar-render.")
        return self


class RenderSuccessResponse(BaseModel):
    success: int = 1
    pid: str
    workflow: str
    webhook_url: str | None = Field(default=None, alias="webhookUrl")


class RenderErrorResponse(BaseModel):
    success: int = 0
    error: str


class CreditEstimateResponse(BaseModel):
    credits: int
    workflow: str
    estimated_duration_seconds: float
