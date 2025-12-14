"""
Configuration settings for HealthCare Plus Voice Assistant
"""

import os
from dataclasses import dataclass, field


@dataclass
class DeepgramConfig:
    """Deepgram STT configuration"""
    api_key: str = ""
    model: str = "nova-3"
    language: str = "multi"
    sample_rate: int = 16000
    encoding: str = "linear16"
    channels: int = 1
    punctuate: bool = True
    smart_format: bool = True
    numerals: bool = True
    interim_results: bool = False
    endpointing: int = 500  # Changed back to 500 to match working version
    
    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.getenv("DEEPGRAM_API_KEY", "")


@dataclass
class OpenAIConfig:
    """OpenAI LLM configuration"""
    api_key: str = ""
    model: str = "gpt-4o-mini"
    max_tokens: int = 80  # Shorter for faster responses
    temperature: float = 0.7
    
    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY", "")


@dataclass
class ElevenLabsConfig:
    """ElevenLabs TTS configuration"""
    api_key: str = ""
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    model: str = "eleven_turbo_v2_5"
    stability: float = 0.5
    similarity_boost: float = 0.5
    
    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.getenv("ELEVENLABS_API_KEY", "")
        if not self.voice_id or self.voice_id == "21m00Tcm4TlvDq8ikWAM":
            self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")


@dataclass
class ServerConfig:
    """WebSocket server configuration"""
    host: str = "localhost"
    port: int = 8765
    
    def __post_init__(self):
        self.host = os.getenv("HOST", "0.0.0.0")  # Default to 0.0.0.0 for Docker
        port_str = os.getenv("PORT")
        if port_str:
            self.port = int(port_str)
            
        # Parse allowed origins (comma separated)
        origins = os.getenv("ALLOWED_ORIGINS", "")
        self.allowed_origins = [o.strip() for o in origins.split(",") if o.strip()]
        
        # Always allow localhost/127.0.0.1 for dev
        if not self.allowed_origins:
            self.allowed_origins = ["*","http://localhost", "http://127.0.0.1", "null", "file://"] # null/file for local files
        else:
            # Ensure localhost is always allowed for testing unless strictly disabled (not doing that here for simplicity)
            server_origins = [
                "http://localhost:8765", 
                "http://localhost", 
                "http://127.0.0.1",
                "http://localhost:8000",
                "http://127.0.0.1:8000", 
                "null", 
                "file://"
            ]
            self.allowed_origins.extend(server_origins)


@dataclass
class Config:
    """Main configuration"""
    deepgram: DeepgramConfig = field(default_factory=DeepgramConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    elevenlabs: ElevenLabsConfig = field(default_factory=ElevenLabsConfig)
    server: ServerConfig = field(default_factory=ServerConfig)


# Global config instance
config = Config()
