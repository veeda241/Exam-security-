"""
ExamGuard Pro - Audio Anomaly Detection Module
Detects suspicious audio patterns during exams.

100% LOCAL - Uses Python audio processing, no external APIs.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import struct
import math

try:
    import wave
    WAVE_AVAILABLE = True
except ImportError:
    WAVE_AVAILABLE = False


# =============================================================================
# Audio Feature Constants
# =============================================================================

# Speech detection thresholds
SPEECH_FREQUENCY_RANGE = (85, 3000)  # Human speech fundamental + harmonics
SILENCE_THRESHOLD = 0.02  # RMS threshold for silence
SPEECH_THRESHOLD = 0.05  # RMS threshold for speech

# Voice patterns
MALE_VOICE_RANGE = (85, 180)    # Hz
FEMALE_VOICE_RANGE = (165, 255)  # Hz
CHILD_VOICE_RANGE = (250, 400)   # Hz

# Suspicious audio patterns
SYNTHETIC_VOICE_PATTERNS = {
    'tts_artifacts': (2000, 4000),  # Common TTS artifact range
    'compression': (8000, 16000),    # Heavy compression artifacts
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class AudioFeatures:
    """Extracted audio features"""
    timestamp: float
    rms: float = 0.0
    peak: float = 0.0
    zero_crossing_rate: float = 0.0
    spectral_centroid: float = 0.0
    spectral_bandwidth: float = 0.0
    spectral_rolloff: float = 0.0
    mfcc: List[float] = field(default_factory=list)
    fundamental_frequency: float = 0.0
    

@dataclass
class VoiceDetection:
    """Voice detection result"""
    is_voice_present: bool = False
    voice_count_estimate: int = 0
    confidence: float = 0.0
    voice_type: str = "unknown"  # male, female, child, multiple
    duration_ms: float = 0.0


@dataclass 
class BackgroundNoiseAnalysis:
    """Background noise analysis"""
    noise_level: float = 0.0  # 0-1
    is_consistent: bool = True
    noise_type: str = "quiet"  # quiet, ambient, noisy, very_noisy
    sudden_changes: int = 0


@dataclass
class SuspiciousAudioEvent:
    """Suspicious audio event"""
    timestamp: str
    event_type: str
    confidence: float
    description: str
    duration_ms: float = 0


@dataclass
class AudioAnalysis:
    """Complete audio analysis result"""
    student_id: str
    timestamp: str
    
    # Voice detection
    voice_detection: VoiceDetection = field(default_factory=VoiceDetection)
    
    # Background analysis
    background_noise: BackgroundNoiseAnalysis = field(default_factory=BackgroundNoiseAnalysis)
    
    # Anomaly detection
    anomaly_score: float = 0.0
    suspicious_events: List[SuspiciousAudioEvent] = field(default_factory=list)
    
    # Summary
    is_suspicious: bool = False
    alerts: List[str] = field(default_factory=list)


# =============================================================================
# Audio Feature Extractor
# =============================================================================

class AudioFeatureExtractor:
    """
    Extracts audio features for analysis.
    Works with raw audio samples.
    """
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        
    def extract_features(self, samples: np.ndarray) -> AudioFeatures:
        """
        Extract audio features from samples.
        
        Args:
            samples: numpy array of audio samples (normalized -1 to 1)
            
        Returns:
            AudioFeatures object
        """
        features = AudioFeatures(
            timestamp=datetime.utcnow().timestamp() * 1000
        )
        
        if len(samples) == 0:
            return features
            
        # Ensure samples are float
        samples = samples.astype(np.float64)
        
        # RMS (Root Mean Square) - measure of signal power
        features.rms = np.sqrt(np.mean(samples**2))
        
        # Peak amplitude
        features.peak = np.max(np.abs(samples))
        
        # Zero Crossing Rate
        features.zero_crossing_rate = self._zero_crossing_rate(samples)
        
        # Spectral features (using FFT)
        freqs, magnitudes = self._compute_spectrum(samples)
        
        if len(magnitudes) > 0:
            features.spectral_centroid = self._spectral_centroid(freqs, magnitudes)
            features.spectral_bandwidth = self._spectral_bandwidth(freqs, magnitudes, features.spectral_centroid)
            features.spectral_rolloff = self._spectral_rolloff(freqs, magnitudes)
            
        # Fundamental frequency (pitch)
        features.fundamental_frequency = self._estimate_fundamental(samples)
        
        # Simplified MFCC (first 13 coefficients approximation)
        features.mfcc = self._compute_simple_mfcc(samples)
        
        return features
    
    def _zero_crossing_rate(self, samples: np.ndarray) -> float:
        """Calculate zero crossing rate"""
        signs = np.sign(samples)
        signs[signs == 0] = 1
        crossings = np.sum(np.abs(np.diff(signs)) / 2)
        return crossings / len(samples)
    
    def _compute_spectrum(self, samples: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Compute frequency spectrum using FFT"""
        n = len(samples)
        if n == 0:
            return np.array([]), np.array([])
            
        # Apply Hanning window
        windowed = samples * np.hanning(n)
        
        # FFT
        fft = np.fft.rfft(windowed)
        magnitudes = np.abs(fft)
        
        # Frequency bins
        freqs = np.fft.rfftfreq(n, 1/self.sample_rate)
        
        return freqs, magnitudes
    
    def _spectral_centroid(self, freqs: np.ndarray, magnitudes: np.ndarray) -> float:
        """Calculate spectral centroid (brightness)"""
        if np.sum(magnitudes) == 0:
            return 0.0
        return np.sum(freqs * magnitudes) / np.sum(magnitudes)
    
    def _spectral_bandwidth(self, freqs: np.ndarray, magnitudes: np.ndarray, centroid: float) -> float:
        """Calculate spectral bandwidth (spread)"""
        if np.sum(magnitudes) == 0:
            return 0.0
        return np.sqrt(np.sum(((freqs - centroid)**2) * magnitudes) / np.sum(magnitudes))
    
    def _spectral_rolloff(self, freqs: np.ndarray, magnitudes: np.ndarray, threshold: float = 0.85) -> float:
        """Calculate spectral rolloff frequency"""
        total = np.sum(magnitudes)
        if total == 0:
            return 0.0
            
        cumsum = np.cumsum(magnitudes)
        rolloff_idx = np.searchsorted(cumsum, threshold * total)
        
        if rolloff_idx < len(freqs):
            return freqs[rolloff_idx]
        return freqs[-1] if len(freqs) > 0 else 0.0
    
    def _estimate_fundamental(self, samples: np.ndarray) -> float:
        """Estimate fundamental frequency using autocorrelation"""
        if len(samples) < 100:
            return 0.0
            
        # Autocorrelation
        n = len(samples)
        correlation = np.correlate(samples, samples, mode='full')[n-1:]
        
        # Find first peak after initial decay
        # Start looking after samples equivalent to max frequency (e.g., 500 Hz)
        min_lag = int(self.sample_rate / 500)  # 500 Hz max
        max_lag = int(self.sample_rate / 50)   # 50 Hz min
        
        if max_lag > len(correlation):
            max_lag = len(correlation) - 1
            
        if min_lag >= max_lag:
            return 0.0
            
        search_range = correlation[min_lag:max_lag]
        
        if len(search_range) == 0:
            return 0.0
            
        # Find peak
        peak_idx = np.argmax(search_range) + min_lag
        
        if peak_idx > 0 and correlation[peak_idx] > 0.3 * correlation[0]:
            return self.sample_rate / peak_idx
            
        return 0.0
    
    def _compute_simple_mfcc(self, samples: np.ndarray, n_mfcc: int = 13) -> List[float]:
        """Compute simplified MFCC-like features"""
        # Get spectrum
        freqs, magnitudes = self._compute_spectrum(samples)
        
        if len(magnitudes) == 0:
            return [0.0] * n_mfcc
            
        # Simple mel-scale approximation using log-spaced bands
        n_bands = n_mfcc * 2
        band_edges = np.logspace(np.log10(100), np.log10(min(8000, self.sample_rate/2)), n_bands + 1)
        
        band_energies = []
        for i in range(n_bands):
            low, high = band_edges[i], band_edges[i+1]
            mask = (freqs >= low) & (freqs < high)
            if np.any(mask):
                band_energies.append(np.sum(magnitudes[mask]**2))
            else:
                band_energies.append(0.0)
                
        # Log compression
        band_energies = np.log1p(band_energies)
        
        # DCT-like transformation (simplified)
        mfcc = []
        for i in range(n_mfcc):
            coeff = 0.0
            for j, energy in enumerate(band_energies):
                coeff += energy * np.cos(np.pi * i * (j + 0.5) / n_bands)
            mfcc.append(coeff)
            
        return mfcc


# =============================================================================
# Voice Detector
# =============================================================================

class VoiceDetector:
    """
    Detects voice presence and characteristics.
    """
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.extractor = AudioFeatureExtractor(sample_rate)
        
    def detect_voice(self, samples: np.ndarray) -> VoiceDetection:
        """
        Detect voice presence in audio samples.
        
        Args:
            samples: Audio samples
            
        Returns:
            VoiceDetection result
        """
        detection = VoiceDetection()
        
        if len(samples) == 0:
            return detection
            
        features = self.extractor.extract_features(samples)
        
        # Check if signal is above silence threshold
        if features.rms < SILENCE_THRESHOLD:
            return detection
            
        # Voice detection heuristics
        confidence = 0.0
        
        # Check for speech-like spectral characteristics
        if SPEECH_FREQUENCY_RANGE[0] < features.spectral_centroid < SPEECH_FREQUENCY_RANGE[1]:
            confidence += 0.3
            
        # Check fundamental frequency (pitch) is in human voice range
        if features.fundamental_frequency > 0:
            if MALE_VOICE_RANGE[0] <= features.fundamental_frequency <= MALE_VOICE_RANGE[1]:
                detection.voice_type = "male"
                confidence += 0.4
            elif FEMALE_VOICE_RANGE[0] <= features.fundamental_frequency <= FEMALE_VOICE_RANGE[1]:
                detection.voice_type = "female"
                confidence += 0.4
            elif CHILD_VOICE_RANGE[0] <= features.fundamental_frequency <= CHILD_VOICE_RANGE[1]:
                detection.voice_type = "child"
                confidence += 0.4
                
        # Check zero crossing rate (speech typically 0.05-0.15)
        if 0.05 < features.zero_crossing_rate < 0.15:
            confidence += 0.2
            
        # Check RMS level
        if features.rms > SPEECH_THRESHOLD:
            confidence += 0.1
            
        detection.confidence = min(1.0, confidence)
        detection.is_voice_present = confidence > 0.5
        detection.duration_ms = len(samples) / self.sample_rate * 1000
        
        return detection
    
    def estimate_voice_count(self, samples: np.ndarray, window_ms: int = 500) -> int:
        """
        Estimate number of distinct voices (rough approximation).
        
        This is a simplified approach - real multi-speaker detection
        would require more sophisticated ML models.
        """
        window_size = int(self.sample_rate * window_ms / 1000)
        
        if len(samples) < window_size:
            return 1 if self.detect_voice(samples).is_voice_present else 0
            
        # Analyze pitch variation across windows
        pitches = []
        
        for i in range(0, len(samples) - window_size, window_size // 2):
            window = samples[i:i + window_size]
            features = self.extractor.extract_features(window)
            
            if features.fundamental_frequency > 0:
                pitches.append(features.fundamental_frequency)
                
        if len(pitches) < 2:
            return 1
            
        # Check for distinct pitch clusters
        pitches = np.array(pitches)
        pitch_std = np.std(pitches)
        
        # Large pitch variation might indicate multiple speakers
        if pitch_std > 50:  # More than 50 Hz variation
            return 2
            
        return 1


# =============================================================================
# Anomaly Detector
# =============================================================================

class AudioAnomalyDetector:
    """
    Detects suspicious audio patterns during exams.
    """
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.extractor = AudioFeatureExtractor(sample_rate)
        self.voice_detector = VoiceDetector(sample_rate)
        
        # Baseline tracking
        self.noise_baseline: Optional[float] = None
        self.feature_history: deque = deque(maxlen=100)
        
    def analyze(self, samples: np.ndarray) -> Tuple[List[SuspiciousAudioEvent], float]:
        """
        Analyze audio for suspicious patterns.
        
        Returns:
            Tuple of (suspicious events, anomaly score)
        """
        events = []
        anomaly_score = 0.0
        
        if len(samples) == 0:
            return events, anomaly_score
            
        features = self.extractor.extract_features(samples)
        self.feature_history.append(features)
        
        # Update noise baseline
        if self.noise_baseline is None:
            self.noise_baseline = features.rms
        else:
            # Slow adaptation
            self.noise_baseline = 0.99 * self.noise_baseline + 0.01 * features.rms
            
        # Check for sudden audio changes
        sudden_change = self._detect_sudden_change(features)
        if sudden_change:
            events.append(sudden_change)
            anomaly_score += 15
            
        # Check for voice presence
        voice = self.voice_detector.detect_voice(samples)
        if voice.is_voice_present:
            # In an exam, sustained voice might be suspicious
            event = SuspiciousAudioEvent(
                timestamp=datetime.utcnow().isoformat(),
                event_type="voice_detected",
                confidence=voice.confidence,
                description=f"Voice detected: {voice.voice_type}",
                duration_ms=voice.duration_ms
            )
            events.append(event)
            anomaly_score += 20 * voice.confidence
            
        # Check for multiple voices
        voice_count = self.voice_detector.estimate_voice_count(samples)
        if voice_count > 1:
            event = SuspiciousAudioEvent(
                timestamp=datetime.utcnow().isoformat(),
                event_type="multiple_voices",
                confidence=0.7,
                description=f"Possible multiple voices detected: {voice_count}"
            )
            events.append(event)
            anomaly_score += 30
            
        # Check for synthetic/TTS voice patterns
        synthetic_score = self._detect_synthetic_voice(features)
        if synthetic_score > 0.5:
            event = SuspiciousAudioEvent(
                timestamp=datetime.utcnow().isoformat(),
                event_type="synthetic_voice",
                confidence=synthetic_score,
                description="Possible text-to-speech or synthetic voice"
            )
            events.append(event)
            anomaly_score += 25 * synthetic_score
            
        return events, min(100, anomaly_score)
    
    def _detect_sudden_change(self, features: AudioFeatures) -> Optional[SuspiciousAudioEvent]:
        """Detect sudden audio level changes"""
        if len(self.feature_history) < 5:
            return None
            
        # Calculate recent average RMS
        recent_rms = [f.rms for f in list(self.feature_history)[-5:-1]]
        avg_rms = np.mean(recent_rms)
        
        # Check for sudden increase
        if features.rms > avg_rms * 3 and features.rms > SPEECH_THRESHOLD:
            return SuspiciousAudioEvent(
                timestamp=datetime.utcnow().isoformat(),
                event_type="sudden_audio_change",
                confidence=0.8,
                description=f"Sudden audio level increase: {features.rms:.3f} vs {avg_rms:.3f}"
            )
            
        return None
    
    def _detect_synthetic_voice(self, features: AudioFeatures) -> float:
        """Detect synthetic/TTS voice characteristics"""
        score = 0.0
        
        # TTS often has very consistent pitch
        if len(self.feature_history) >= 10:
            recent_pitches = [f.fundamental_frequency for f in list(self.feature_history)[-10:]]
            recent_pitches = [p for p in recent_pitches if p > 0]
            
            if len(recent_pitches) >= 5:
                pitch_std = np.std(recent_pitches)
                
                # Very low pitch variation is suspicious
                if pitch_std < 5:  # Less than 5 Hz variation
                    score += 0.4
                    
        # Check spectral characteristics
        # TTS often has less high-frequency content
        if features.spectral_rolloff < 2000:
            score += 0.3
            
        # Check for unusual spectral regularity
        if features.spectral_bandwidth < 500:
            score += 0.2
            
        return min(1.0, score)
    
    def analyze_background(self, samples: np.ndarray) -> BackgroundNoiseAnalysis:
        """Analyze background noise characteristics"""
        analysis = BackgroundNoiseAnalysis()
        
        if len(samples) == 0:
            return analysis
            
        features = self.extractor.extract_features(samples)
        
        # Noise level classification
        analysis.noise_level = features.rms
        
        if features.rms < 0.01:
            analysis.noise_type = "quiet"
        elif features.rms < 0.03:
            analysis.noise_type = "ambient"
        elif features.rms < 0.1:
            analysis.noise_type = "noisy"
        else:
            analysis.noise_type = "very_noisy"
            
        # Check consistency
        if len(self.feature_history) >= 10:
            recent_rms = [f.rms for f in list(self.feature_history)[-10:]]
            rms_std = np.std(recent_rms)
            
            analysis.is_consistent = rms_std < 0.05
            
            # Count sudden changes
            for i in range(1, len(recent_rms)):
                if abs(recent_rms[i] - recent_rms[i-1]) > 0.1:
                    analysis.sudden_changes += 1
                    
        return analysis


# =============================================================================
# Audio Analysis Service
# =============================================================================

class AudioAnalysisService:
    """
    Main service for audio analysis.
    """
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.analyzers: Dict[str, AudioAnomalyDetector] = {}
        self.analysis_history: Dict[str, List[AudioAnalysis]] = {}
        
    def get_analyzer(self, student_id: str) -> AudioAnomalyDetector:
        """Get or create analyzer for student"""
        if student_id not in self.analyzers:
            self.analyzers[student_id] = AudioAnomalyDetector(self.sample_rate)
        return self.analyzers[student_id]
    
    def process_audio(self, student_id: str, audio_data: bytes, 
                      format_type: str = "pcm16") -> AudioAnalysis:
        """
        Process audio data and return analysis.
        
        Args:
            student_id: Student identifier
            audio_data: Raw audio bytes
            format_type: Audio format (pcm16, float32, etc.)
            
        Returns:
            AudioAnalysis result
        """
        # Convert bytes to numpy array
        samples = self._decode_audio(audio_data, format_type)
        
        return self.analyze_samples(student_id, samples)
    
    def analyze_samples(self, student_id: str, samples: np.ndarray) -> AudioAnalysis:
        """
        Analyze audio samples.
        
        Args:
            student_id: Student identifier
            samples: Numpy array of audio samples
            
        Returns:
            AudioAnalysis result
        """
        analyzer = self.get_analyzer(student_id)
        
        analysis = AudioAnalysis(
            student_id=student_id,
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Voice detection
        voice_detector = VoiceDetector(self.sample_rate)
        analysis.voice_detection = voice_detector.detect_voice(samples)
        analysis.voice_detection.voice_count_estimate = voice_detector.estimate_voice_count(samples)
        
        # Background noise analysis
        analysis.background_noise = analyzer.analyze_background(samples)
        
        # Anomaly detection
        events, anomaly_score = analyzer.analyze(samples)
        analysis.suspicious_events = events
        analysis.anomaly_score = anomaly_score
        
        # Generate alerts
        analysis.is_suspicious = anomaly_score > 30
        analysis.alerts = self._generate_alerts(analysis)
        
        # Store in history
        if student_id not in self.analysis_history:
            self.analysis_history[student_id] = []
            
        self.analysis_history[student_id].append(analysis)
        
        # Keep only last 100 analyses
        if len(self.analysis_history[student_id]) > 100:
            self.analysis_history[student_id] = self.analysis_history[student_id][-100:]
            
        return analysis
    
    def _decode_audio(self, audio_data: bytes, format_type: str) -> np.ndarray:
        """Decode audio bytes to numpy array"""
        if format_type == "pcm16":
            # 16-bit PCM
            samples = np.frombuffer(audio_data, dtype=np.int16)
            return samples.astype(np.float64) / 32768.0
            
        elif format_type == "float32":
            # 32-bit float
            return np.frombuffer(audio_data, dtype=np.float32)
            
        elif format_type == "pcm8":
            # 8-bit PCM
            samples = np.frombuffer(audio_data, dtype=np.uint8)
            return (samples.astype(np.float64) - 128) / 128.0
            
        else:
            # Assume PCM16 as default
            samples = np.frombuffer(audio_data, dtype=np.int16)
            return samples.astype(np.float64) / 32768.0
    
    def _generate_alerts(self, analysis: AudioAnalysis) -> List[str]:
        """Generate alerts based on analysis"""
        alerts = []
        
        if analysis.voice_detection.is_voice_present:
            if analysis.voice_detection.voice_count_estimate > 1:
                alerts.append("🎤 Multiple voices detected")
            else:
                alerts.append(f"🎤 Voice detected ({analysis.voice_detection.voice_type})")
                
        if analysis.background_noise.noise_type == "very_noisy":
            alerts.append("🔊 High background noise")
            
        if not analysis.background_noise.is_consistent:
            alerts.append("⚠️ Inconsistent audio environment")
            
        for event in analysis.suspicious_events:
            if event.event_type == "synthetic_voice":
                alerts.append("🤖 Possible synthetic/TTS voice")
            elif event.event_type == "sudden_audio_change":
                alerts.append("📢 Sudden audio change")
                
        return alerts
    
    def get_history(self, student_id: str) -> List[AudioAnalysis]:
        """Get analysis history for student"""
        return self.analysis_history.get(student_id, [])
    
    def reset_analyzer(self, student_id: str):
        """Reset analyzer for new session"""
        if student_id in self.analyzers:
            del self.analyzers[student_id]


# =============================================================================
# Singleton Instance
# =============================================================================

_audio_service: Optional[AudioAnalysisService] = None

def get_audio_service() -> AudioAnalysisService:
    """Get singleton audio analysis service"""
    global _audio_service
    if _audio_service is None:
        _audio_service = AudioAnalysisService()
    return _audio_service
