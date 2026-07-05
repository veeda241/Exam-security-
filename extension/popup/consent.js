/**
 * Consent screen — dual retention policy + biometric opt-out.
 */
(function () {
  const consentSection = document.getElementById('consent-section');
  const setupSection = document.getElementById('setup-section');
  const acceptBtn = document.getElementById('consent-accept');
  const declineBiometricBtn = document.getElementById('consent-decline-biometric');
  const retentionModeEl = document.getElementById('retention-mode-label');

  if (!consentSection) return;

  const policy = {
    retention_mode: 'standard',
    screenshot_days: 30,
    biometric_monitoring: 'required',
    alternative_mode: 'reduced_monitoring',
  };

  chrome.storage.session.get(['exam_ruleset'], (result) => {
    const ruleset = result.exam_ruleset || {};
    const retention = ruleset.retention || {};
    if (retention.mode === 'extended') {
      policy.retention_mode = 'extended';
      policy.screenshot_days = retention.extended_screenshot_days || 90;
    }
    if (ruleset.biometric_monitoring === 'optional_with_alternative') {
      policy.biometric_monitoring = 'optional_with_alternative';
    }
    if (retentionModeEl) {
      retentionModeEl.textContent =
        policy.retention_mode === 'extended'
          ? `Extended retention (${policy.screenshot_days} days for flagged screenshots)`
          : `Standard retention (${policy.screenshot_days} days for flagged screenshots)`;
    }
  });

  acceptBtn?.addEventListener('click', () => {
    const consent = {
      consented_at: new Date().toISOString(),
      retention_mode: policy.retention_mode,
      biometric_consent: true,
      monitoring_tier: 'full',
      policy_version: 1,
    };
    chrome.storage.session.set({ consent_metadata: consent, consent_given: true }, () => {
      consentSection.classList.add('hidden');
      setupSection?.classList.remove('hidden');
    });
  });

  declineBiometricBtn?.addEventListener('click', () => {
    if (policy.biometric_monitoring !== 'optional_with_alternative') return;
    const consent = {
      consented_at: new Date().toISOString(),
      retention_mode: policy.retention_mode,
      biometric_consent: false,
      monitoring_tier: 'reduced',
      policy_version: 1,
    };
    chrome.storage.session.set({ consent_metadata: consent, consent_given: true }, () => {
      consentSection.classList.add('hidden');
      setupSection?.classList.remove('hidden');
    });
  });
})();
