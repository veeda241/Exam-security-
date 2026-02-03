/**
 * ExamGuard Pro - Capture Page v2.0
 * Premium UX for handling media permissions and starting the session
 */

const screenCard = document.getElementById('screen-card');
const webcamCard = document.getElementById('webcam-card');
const finalBtn = document.getElementById('final-btn');
const screenStatusIcon = document.getElementById('screen-status-icon');
const webcamStatusIcon = document.getElementById('webcam-status-icon');
const syncLoader = document.getElementById('sync-loader');

// Global capture instance
const capture = new ExamCapture();
let screenGranted = false;
let webcamGranted = false;

// ==================== PERMISSION REQUESTS ====================

screenCard.addEventListener('click', async () => {
    if (screenGranted) return;

    screenStatusIcon.textContent = '⏳';
    try {
        const result = await capture.startScreenCapture();
        if (result.success) {
            screenGranted = true;
            screenStatusIcon.textContent = '✅';
            screenCard.classList.add('granted');
            screenCard.classList.remove('denied');
            showToast('Screen sharing enabled', 'success');
        } else {
            throw new Error(result.error || 'User cancelled');
        }
    } catch (err) {
        screenStatusIcon.textContent = '❌';
        screenCard.classList.add('denied');
        showToast('Screen share required', 'error');
    }
    updateFinalButton();
});

webcamCard.addEventListener('click', async () => {
    if (webcamGranted) return;

    webcamStatusIcon.textContent = '⏳';
    try {
        const result = await capture.startWebcamCapture();
        if (result.success) {
            webcamGranted = true;
            webcamStatusIcon.textContent = '✅';
            webcamCard.classList.add('granted');
            webcamCard.classList.remove('denied');
            showToast('Webcam access granted', 'success');
        } else {
            throw new Error(result.error || 'Permission denied');
        }
    } catch (err) {
        webcamStatusIcon.textContent = '❌';
        webcamCard.classList.add('denied');
        showToast('Camera access required', 'error');
    }
    updateFinalButton();
});

// ==================== STATE MANAGEMENT ====================

function updateFinalButton() {
    finalBtn.disabled = !(screenGranted && webcamGranted);
    if (!finalBtn.disabled) {
        finalBtn.style.animation = 'pulse 2s infinite';
    }
}

finalBtn.addEventListener('click', async () => {
    finalBtn.disabled = true;
    finalBtn.textContent = 'Initializing...';
    syncLoader.style.display = 'flex';

    // Small delay to ensure everything is synced
    setTimeout(() => {
        chrome.runtime.sendMessage({
            type: 'CAPTURE_READY',
            status: {
                screen: true,
                webcam: true,
                timestamp: Date.now()
            }
        }, (response) => {
            if (response && response.success) {
                // Background will minimize this window
                finalBtn.textContent = 'Session Active';
            } else {
                showToast('Setup failed. Please retry.', 'error');
                finalBtn.disabled = false;
                finalBtn.textContent = 'Launch Secure Session';
                syncLoader.style.display = 'none';
            }
        });
    }, 1500);
});

// ==================== UI UTILS ====================

function showToast(message, type) {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        left: 50%;
        transform: translateX(-50%);
        background: ${type === 'success' ? '#10b981' : '#ef4444'};
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        animation: slideUp 0.3s ease forwards;
        z-index: 1000;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideDown 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Add animations
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 8px 20px var(--primary-glow); }
        50% { transform: scale(1.02); box-shadow: 0 12px 30px var(--primary-glow); }
        100% { transform: scale(1); box-shadow: 0 8px 20px var(--primary-glow); }
    }
    @keyframes slideUp {
        from { transform: translateX(-50%) translateY(20px); opacity: 0; }
        to { transform: translateX(-50%) translateY(0); opacity: 1; }
    }
`;
document.head.appendChild(style);
