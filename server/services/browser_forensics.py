"""
ExamGuard Pro - Browser Forensics Module
Detects virtual machines, remote desktop, browser extensions, and other cheating tools.

100% LOCAL - Pure JavaScript/Python detection, no external APIs.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import re


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class BrowserFingerprint:
    """Browser and system fingerprint"""
    user_agent: str = ""
    platform: str = ""
    vendor: str = ""
    language: str = ""
    languages: List[str] = field(default_factory=list)
    timezone: str = ""
    timezone_offset: int = 0
    screen_width: int = 0
    screen_height: int = 0
    available_width: int = 0
    available_height: int = 0
    color_depth: int = 0
    pixel_ratio: float = 1.0
    hardware_concurrency: int = 0
    device_memory: float = 0
    max_touch_points: int = 0
    webgl_vendor: str = ""
    webgl_renderer: str = ""
    audio_fingerprint: str = ""
    canvas_fingerprint: str = ""
    fonts: List[str] = field(default_factory=list)
    plugins: List[str] = field(default_factory=list)


@dataclass
class VMDetection:
    """Virtual machine detection result"""
    is_vm: bool = False
    confidence: float = 0.0
    indicators: List[str] = field(default_factory=list)
    vm_type: Optional[str] = None


@dataclass
class RemoteDesktopDetection:
    """Remote desktop detection result"""
    is_remote: bool = False
    confidence: float = 0.0
    indicators: List[str] = field(default_factory=list)
    remote_type: Optional[str] = None


@dataclass
class ExtensionDetection:
    """Suspicious extension detection"""
    suspicious_count: int = 0
    extensions: List[Dict] = field(default_factory=list)
    risk_level: str = "low"


@dataclass
class ScreenShareDetection:
    """Screen sharing detection"""
    is_sharing: bool = False
    confidence: float = 0.0
    indicators: List[str] = field(default_factory=list)


@dataclass
class ForensicsAnalysis:
    """Complete forensics analysis result"""
    student_id: str
    timestamp: str
    fingerprint: BrowserFingerprint = field(default_factory=BrowserFingerprint)
    vm_detection: VMDetection = field(default_factory=VMDetection)
    remote_desktop: RemoteDesktopDetection = field(default_factory=RemoteDesktopDetection)
    extensions: ExtensionDetection = field(default_factory=ExtensionDetection)
    screen_share: ScreenShareDetection = field(default_factory=ScreenShareDetection)
    overall_risk_score: float = 0.0
    alerts: List[str] = field(default_factory=list)


# =============================================================================
# VM Detection Patterns
# =============================================================================

VM_INDICATORS = {
    'webgl_renderer': [
        ('vmware', 'VMware'),
        ('virtualbox', 'VirtualBox'),
        ('parallels', 'Parallels'),
        ('hyper-v', 'Hyper-V'),
        ('qemu', 'QEMU'),
        ('kvm', 'KVM'),
        ('xen', 'Xen'),
        ('citrix', 'Citrix'),
        ('llvmpipe', 'Software Renderer (possible VM)'),
        ('swiftshader', 'SwiftShader (headless/VM)'),
        ('mesa', 'Mesa (possible VM)'),
    ],
    'webgl_vendor': [
        ('vmware', 'VMware'),
        ('microsoft basic render', 'Virtual'),
        ('google swiftshader', 'SwiftShader'),
    ],
    'user_agent': [
        ('headless', 'Headless Browser'),
        ('phantomjs', 'PhantomJS'),
        ('selenium', 'Selenium'),
        ('puppeteer', 'Puppeteer'),
        ('playwright', 'Playwright'),
    ],
    'platform': [
        ('linux.*x86_64', 'Possible VM'),
    ]
}

SUSPICIOUS_SCREEN_SIZES = [
    (800, 600),    # Common VM default
    (1024, 768),   # Common VM size
    (1280, 720),   # Suspiciously small for exams
]

VM_HARDWARE_PATTERNS = {
    'low_cores': lambda cores: cores <= 2,
    'low_memory': lambda mem: mem <= 4,
    'unusual_touch': lambda touch: touch == 0,
}


# =============================================================================
# Remote Desktop Detection Patterns
# =============================================================================

REMOTE_DESKTOP_INDICATORS = {
    'user_agent': [
        ('anydesk', 'AnyDesk'),
        ('teamviewer', 'TeamViewer'),
        ('chrome remote desktop', 'Chrome Remote Desktop'),
        ('parsec', 'Parsec'),
        ('rdp', 'Remote Desktop'),
    ],
    'screen_patterns': [
        # Screen != available screen (taskbar/toolbar overlay)
        lambda s, a: (s[0] - a[0]) > 100 or (s[1] - a[1]) > 100,
    ],
    'timing_patterns': [
        # High latency in user interactions
    ]
}


# =============================================================================
# Suspicious Extension Patterns
# =============================================================================

SUSPICIOUS_EXTENSIONS = [
    # Screen recording
    {'pattern': r'screen.*record', 'category': 'screen_recording', 'risk': 'high'},
    {'pattern': r'loom', 'category': 'screen_recording', 'risk': 'high'},
    {'pattern': r'screencastify', 'category': 'screen_recording', 'risk': 'high'},
    
    # Tab management / hiding
    {'pattern': r'tab.*hide', 'category': 'tab_hiding', 'risk': 'high'},
    {'pattern': r'panic.*button', 'category': 'tab_hiding', 'risk': 'high'},
    {'pattern': r'boss.*key', 'category': 'tab_hiding', 'risk': 'high'},
    
    # Auto-answer / AI
    {'pattern': r'chatgpt', 'category': 'ai_assistant', 'risk': 'critical'},
    {'pattern': r'copilot', 'category': 'ai_assistant', 'risk': 'medium'},  # Could be legit
    {'pattern': r'quillbot', 'category': 'ai_writing', 'risk': 'high'},
    {'pattern': r'grammarly', 'category': 'writing_assist', 'risk': 'low'},
    
    # Remote access
    {'pattern': r'anydesk', 'category': 'remote_access', 'risk': 'critical'},
    {'pattern': r'teamviewer', 'category': 'remote_access', 'risk': 'critical'},
    {'pattern': r'remote.*desktop', 'category': 'remote_access', 'risk': 'critical'},
    
    # Search / lookup
    {'pattern': r'google.*lens', 'category': 'search', 'risk': 'high'},
    {'pattern': r'reverse.*image', 'category': 'search', 'risk': 'high'},
    
    # Automation
    {'pattern': r'autofill', 'category': 'automation', 'risk': 'medium'},
    {'pattern': r'selenium', 'category': 'automation', 'risk': 'critical'},
    {'pattern': r'puppeteer', 'category': 'automation', 'risk': 'critical'},
    
    # VPN / Proxy (can be used to bypass restrictions)
    {'pattern': r'vpn', 'category': 'vpn', 'risk': 'medium'},
    {'pattern': r'proxy', 'category': 'proxy', 'risk': 'medium'},
]


# =============================================================================
# Forensics Analyzer
# =============================================================================

class ForensicsAnalyzer:
    """
    Analyzes browser forensics data for cheating indicators.
    """
    
    def __init__(self):
        self.baseline_fingerprints: Dict[str, BrowserFingerprint] = {}
        
    def analyze(self, student_id: str, data: dict) -> ForensicsAnalysis:
        """
        Perform complete forensics analysis.
        
        Args:
            student_id: Student identifier
            data: Raw forensics data from client
            
        Returns:
            Complete ForensicsAnalysis result
        """
        analysis = ForensicsAnalysis(
            student_id=student_id,
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Parse fingerprint
        analysis.fingerprint = self._parse_fingerprint(data)
        
        # Run detections
        analysis.vm_detection = self._detect_vm(analysis.fingerprint)
        analysis.remote_desktop = self._detect_remote_desktop(analysis.fingerprint, data)
        analysis.extensions = self._detect_extensions(data.get('extensions', []))
        analysis.screen_share = self._detect_screen_share(data)
        
        # Calculate overall risk
        analysis.overall_risk_score = self._calculate_risk_score(analysis)
        analysis.alerts = self._generate_alerts(analysis)
        
        # Check for fingerprint changes
        self._check_fingerprint_consistency(student_id, analysis.fingerprint, analysis)
        
        return analysis
    
    def _parse_fingerprint(self, data: dict) -> BrowserFingerprint:
        """Parse browser fingerprint from raw data"""
        return BrowserFingerprint(
            user_agent=data.get('userAgent', ''),
            platform=data.get('platform', ''),
            vendor=data.get('vendor', ''),
            language=data.get('language', ''),
            languages=data.get('languages', []),
            timezone=data.get('timezone', ''),
            timezone_offset=data.get('timezoneOffset', 0),
            screen_width=data.get('screenWidth', 0),
            screen_height=data.get('screenHeight', 0),
            available_width=data.get('availWidth', 0),
            available_height=data.get('availHeight', 0),
            color_depth=data.get('colorDepth', 0),
            pixel_ratio=data.get('pixelRatio', 1.0),
            hardware_concurrency=data.get('hardwareConcurrency', 0),
            device_memory=data.get('deviceMemory', 0),
            max_touch_points=data.get('maxTouchPoints', 0),
            webgl_vendor=data.get('webglVendor', ''),
            webgl_renderer=data.get('webglRenderer', ''),
            audio_fingerprint=data.get('audioFingerprint', ''),
            canvas_fingerprint=data.get('canvasFingerprint', ''),
            fonts=data.get('fonts', []),
            plugins=data.get('plugins', []),
        )
    
    def _detect_vm(self, fp: BrowserFingerprint) -> VMDetection:
        """Detect virtual machine indicators"""
        detection = VMDetection()
        indicators = []
        confidence = 0.0
        
        # Check WebGL renderer
        renderer_lower = fp.webgl_renderer.lower()
        for pattern, vm_name in VM_INDICATORS['webgl_renderer']:
            if pattern in renderer_lower:
                indicators.append(f"WebGL renderer indicates {vm_name}")
                confidence += 30
                detection.vm_type = vm_name
                
        # Check WebGL vendor
        vendor_lower = fp.webgl_vendor.lower()
        for pattern, vm_name in VM_INDICATORS['webgl_vendor']:
            if pattern in vendor_lower:
                indicators.append(f"WebGL vendor indicates {vm_name}")
                confidence += 25
                
        # Check user agent
        ua_lower = fp.user_agent.lower()
        for pattern, tool_name in VM_INDICATORS['user_agent']:
            if pattern in ua_lower:
                indicators.append(f"User agent indicates {tool_name}")
                confidence += 40
                
        # Check hardware
        if fp.hardware_concurrency > 0 and fp.hardware_concurrency <= 2:
            indicators.append("Low CPU cores (typical for VMs)")
            confidence += 15
            
        if fp.device_memory > 0 and fp.device_memory <= 4:
            indicators.append("Low device memory (typical for VMs)")
            confidence += 15
            
        # Check screen size
        if (fp.screen_width, fp.screen_height) in SUSPICIOUS_SCREEN_SIZES:
            indicators.append("Suspicious screen resolution")
            confidence += 10
            
        # Pixel ratio check
        if fp.pixel_ratio == 1.0 and fp.screen_width >= 1920:
            indicators.append("Unusual pixel ratio for high-res display")
            confidence += 5
            
        detection.confidence = min(100, confidence)
        detection.is_vm = confidence >= 40
        detection.indicators = indicators
        
        return detection
    
    def _detect_remote_desktop(self, fp: BrowserFingerprint, data: dict) -> RemoteDesktopDetection:
        """Detect remote desktop indicators"""
        detection = RemoteDesktopDetection()
        indicators = []
        confidence = 0.0
        
        # Check user agent for remote tools
        ua_lower = fp.user_agent.lower()
        for pattern, tool_name in REMOTE_DESKTOP_INDICATORS['user_agent']:
            if pattern in ua_lower:
                indicators.append(f"Remote desktop tool detected: {tool_name}")
                confidence += 50
                detection.remote_type = tool_name
                
        # Check screen vs available screen mismatch
        width_diff = fp.screen_width - fp.available_width
        height_diff = fp.screen_height - fp.available_height
        
        if width_diff > 200 or height_diff > 200:
            indicators.append("Large screen/available screen mismatch (possible remote session)")
            confidence += 20
            
        # Check for unusual aspect ratios (remote sessions often have odd dimensions)
        if fp.screen_width > 0 and fp.screen_height > 0:
            aspect_ratio = fp.screen_width / fp.screen_height
            
            # Standard ratios: 16:9 (1.78), 16:10 (1.6), 4:3 (1.33), 21:9 (2.33)
            standard_ratios = [1.33, 1.6, 1.78, 2.33]
            
            if not any(abs(aspect_ratio - r) < 0.05 for r in standard_ratios):
                indicators.append(f"Non-standard aspect ratio: {aspect_ratio:.2f}")
                confidence += 10
                
        # Check interaction latency (if provided)
        avg_latency = data.get('avgInteractionLatency', 0)
        if avg_latency > 100:  # More than 100ms average latency
            indicators.append(f"High interaction latency: {avg_latency}ms")
            confidence += 25
            
        detection.confidence = min(100, confidence)
        detection.is_remote = confidence >= 40
        detection.indicators = indicators
        
        return detection
    
    def _detect_extensions(self, extensions: List[dict]) -> ExtensionDetection:
        """Detect suspicious browser extensions"""
        detection = ExtensionDetection()
        suspicious = []
        
        for ext in extensions:
            ext_name = ext.get('name', '').lower()
            ext_id = ext.get('id', '')
            
            for pattern_info in SUSPICIOUS_EXTENSIONS:
                if re.search(pattern_info['pattern'], ext_name, re.IGNORECASE):
                    suspicious.append({
                        'name': ext.get('name', 'Unknown'),
                        'id': ext_id,
                        'category': pattern_info['category'],
                        'risk': pattern_info['risk'],
                    })
                    break
                    
        detection.extensions = suspicious
        detection.suspicious_count = len(suspicious)
        
        # Determine overall risk level
        risk_levels = [e['risk'] for e in suspicious]
        
        if 'critical' in risk_levels:
            detection.risk_level = 'critical'
        elif 'high' in risk_levels:
            detection.risk_level = 'high'
        elif 'medium' in risk_levels:
            detection.risk_level = 'medium'
        else:
            detection.risk_level = 'low'
            
        return detection
    
    def _detect_screen_share(self, data: dict) -> ScreenShareDetection:
        """Detect screen sharing indicators"""
        detection = ScreenShareDetection()
        indicators = []
        confidence = 0.0
        
        # Check if screen share API is active
        if data.get('displayMediaActive', False):
            indicators.append("Screen sharing API is active")
            confidence += 80
            
        # Check for screen recording indicators
        if data.get('mediaRecorderActive', False):
            indicators.append("Media recorder is active")
            confidence += 40
            
        # Check for multiple displays
        if data.get('screenCount', 1) > 1:
            indicators.append(f"Multiple displays detected: {data.get('screenCount')}")
            confidence += 15
            
        # Check if window is not focused (might be sharing another window)
        if not data.get('windowFocused', True):
            indicators.append("Browser window not focused")
            confidence += 10
            
        detection.confidence = min(100, confidence)
        detection.is_sharing = confidence >= 50
        detection.indicators = indicators
        
        return detection
    
    def _calculate_risk_score(self, analysis: ForensicsAnalysis) -> float:
        """Calculate overall risk score"""
        score = 0.0
        
        # VM detection contributes up to 30 points
        if analysis.vm_detection.is_vm:
            score += min(30, analysis.vm_detection.confidence * 0.3)
            
        # Remote desktop contributes up to 35 points
        if analysis.remote_desktop.is_remote:
            score += min(35, analysis.remote_desktop.confidence * 0.35)
            
        # Extensions contribute up to 25 points
        ext_risk = analysis.extensions.risk_level
        if ext_risk == 'critical':
            score += 25
        elif ext_risk == 'high':
            score += 15
        elif ext_risk == 'medium':
            score += 8
            
        # Screen share contributes up to 30 points
        if analysis.screen_share.is_sharing:
            score += min(30, analysis.screen_share.confidence * 0.3)
            
        return min(100, score)
    
    def _generate_alerts(self, analysis: ForensicsAnalysis) -> List[str]:
        """Generate alerts based on analysis"""
        alerts = []
        
        if analysis.vm_detection.is_vm:
            vm_type = analysis.vm_detection.vm_type or "Unknown"
            alerts.append(f"🖥️ Virtual machine detected: {vm_type}")
            
        if analysis.remote_desktop.is_remote:
            rd_type = analysis.remote_desktop.remote_type or "Unknown"
            alerts.append(f"🖱️ Remote desktop detected: {rd_type}")
            
        if analysis.extensions.risk_level in ['critical', 'high']:
            count = analysis.extensions.suspicious_count
            alerts.append(f"🔌 {count} suspicious extension(s) detected")
            
        if analysis.screen_share.is_sharing:
            alerts.append("📺 Screen sharing detected")
            
        return alerts
    
    def _check_fingerprint_consistency(self, student_id: str, 
                                        fingerprint: BrowserFingerprint,
                                        analysis: ForensicsAnalysis):
        """Check if fingerprint matches baseline"""
        if student_id not in self.baseline_fingerprints:
            # Store as baseline
            self.baseline_fingerprints[student_id] = fingerprint
            return
            
        baseline = self.baseline_fingerprints[student_id]
        
        # Check for significant changes
        changes = []
        
        if baseline.user_agent != fingerprint.user_agent:
            changes.append("User agent changed")
            
        if baseline.platform != fingerprint.platform:
            changes.append("Platform changed")
            
        if baseline.timezone != fingerprint.timezone:
            changes.append("Timezone changed")
            
        if baseline.screen_width != fingerprint.screen_width or \
           baseline.screen_height != fingerprint.screen_height:
            changes.append("Screen resolution changed")
            
        if baseline.hardware_concurrency != fingerprint.hardware_concurrency:
            changes.append("CPU cores changed")
            
        if baseline.canvas_fingerprint != fingerprint.canvas_fingerprint:
            changes.append("Canvas fingerprint changed")
            
        if changes:
            analysis.alerts.append(f"⚠️ Browser fingerprint changed: {', '.join(changes)}")
            analysis.overall_risk_score = min(100, analysis.overall_risk_score + len(changes) * 5)


# =============================================================================
# Forensics Service
# =============================================================================

class ForensicsService:
    """
    Main service for browser forensics.
    """
    
    def __init__(self):
        self.analyzer = ForensicsAnalyzer()
        self.analysis_history: Dict[str, List[ForensicsAnalysis]] = {}
        
    def analyze(self, student_id: str, data: dict) -> ForensicsAnalysis:
        """Perform forensics analysis"""
        analysis = self.analyzer.analyze(student_id, data)
        
        # Store in history
        if student_id not in self.analysis_history:
            self.analysis_history[student_id] = []
            
        self.analysis_history[student_id].append(analysis)
        
        # Keep only last 100 analyses per student
        if len(self.analysis_history[student_id]) > 100:
            self.analysis_history[student_id] = self.analysis_history[student_id][-100:]
            
        return analysis
    
    def get_history(self, student_id: str) -> List[ForensicsAnalysis]:
        """Get analysis history for student"""
        return self.analysis_history.get(student_id, [])
    
    def get_all_alerts(self) -> Dict[str, List[str]]:
        """Get all current alerts by student"""
        alerts = {}
        
        for student_id, history in self.analysis_history.items():
            if history:
                latest = history[-1]
                if latest.alerts:
                    alerts[student_id] = latest.alerts
                    
        return alerts


# =============================================================================
# Singleton Instance
# =============================================================================

_forensics_service: Optional[ForensicsService] = None

def get_forensics_service() -> ForensicsService:
    """Get singleton forensics service"""
    global _forensics_service
    if _forensics_service is None:
        _forensics_service = ForensicsService()
    return _forensics_service
