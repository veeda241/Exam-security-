(function () {
  if (window.top !== window) {
    return;
  }

  const ANALYZE_INTERVAL_MS = 8000;
  const INITIAL_DELAY_MS = 1200;

  function extractPageSignals() {
    const meta = {};
    try {
      document.querySelectorAll('meta[name], meta[property]').forEach((node) => {
        const key = (node.getAttribute('name') || node.getAttribute('property') || '').toLowerCase();
        if (!key) return;
        meta[key] = String(node.getAttribute('content') || '').slice(0, 240);
      });
    } catch (error) {
      // Some pages block DOM reads
    }

    const hasVideoPlayer = !!document.querySelector(
      'video, ytd-player, .html5-video-player, [class*="video-player"], [data-testid*="video"]'
    );
    const hasChatUi = !!document.querySelector(
      '[class*="chat" i], [id*="chat" i], textarea[placeholder*="message" i], [data-testid*="chat" i], [aria-label*="chat" i]'
    );
    const hasCodeEditor = !!document.querySelector(
      '.monaco-editor, .CodeMirror, .cm-editor, pre code, .highlight-source'
    );
    const hasQuizForm = !!document.querySelector(
      'input[type="radio"], input[type="checkbox"], .quiz, [class*="question" i], form[action*="quiz" i], [class*="kahoot" i], [class*="quizizz" i]'
    );
    const hasEducationUi = !!document.querySelector(
      '[class*="course" i], [class*="lesson" i], [class*="module" i], [class*="lms" i], [id*="course" i], [data-testid*="course" i], nav[aria-label*="course" i]'
    );
    const pageTextSample = sanitizeText(document.body?.innerText || '', 1200).toLowerCase();
    const hasEducationText = /\b(my courses|course dashboard|enrolled|learning path|lesson module|watch lecture|google classroom)\b/.test(pageTextSample);
    const hasQuizText = /\b(start quiz|submit quiz|question \d+ of|kahoot|quizizz|practice quiz)\b/.test(pageTextSample);
    const hasFeedUi = !!document.querySelector(
      '[role="feed"], [class*="feed" i], [class*="timeline" i], [data-testid*="feed" i]'
    );

    const scriptHosts = [];
    try {
      document.querySelectorAll('script[src]').forEach((node) => {
        try {
          const host = new URL(node.src, location.href).hostname.replace(/^www\./, '').toLowerCase();
          if (host && !scriptHosts.includes(host)) scriptHosts.push(host);
        } catch (error) {
          // Ignore malformed script URLs
        }
      });
    } catch (error) {
      // Ignore
    }

    return {
      meta,
      has_video_player: hasVideoPlayer,
      has_chat_ui: hasChatUi,
      has_code_editor: hasCodeEditor,
      has_quiz_form: hasQuizForm || hasQuizText,
      has_education_ui: hasEducationUi || hasEducationText,
      has_feed_ui: hasFeedUi,
      script_hosts: scriptHosts.slice(0, 20),
      script_count: document.querySelectorAll('script').length,
      iframe_count: document.querySelectorAll('iframe').length,
    };
  }

  let pageStartedAt = Date.now();
  let lastSignature = '';
  let intervalId = null;
  let pendingTimer = null;
  let hiddenCount = 0;
  let focusLostCount = 0;

  function sanitizeText(value, limit = 3500) {
    return String(value || '')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, limit);
  }

  function extractYouTubeMetadata() {
    const isYouTube = location.hostname.includes('youtube.com');
    if (!isYouTube) {
      return {
        youtube_title: '',
        youtube_channel: '',
        page_type: 'generic',
      };
    }

    const titleCandidates = [
      document.querySelector('h1 yt-formatted-string')?.textContent,
      document.querySelector('h1.title yt-formatted-string')?.textContent,
      document.querySelector('meta[name="title"]')?.getAttribute('content'),
      document.querySelector('meta[property="og:title"]')?.getAttribute('content'),
    ];

    const channelCandidates = [
      document.querySelector('ytd-channel-name a')?.textContent,
      document.querySelector('#channel-name a')?.textContent,
      document.querySelector('meta[property="og:site_name"]')?.getAttribute('content'),
    ];

    return {
      youtube_title: sanitizeText(titleCandidates.find(Boolean)),
      youtube_channel: sanitizeText(channelCandidates.find(Boolean)),
      page_type: 'youtube',
    };
  }

  function buildPageContext() {
    const youtube = extractYouTubeMetadata();
    const bodyText = sanitizeText(document.body?.innerText || document.documentElement?.innerText || '');
    const title = sanitizeText(document.title || document.querySelector('meta[property="og:title"]')?.getAttribute('content') || '');

    return {
      url: location.href,
      domain: location.hostname.replace(/^www\./, '').toLowerCase(),
      path: location.pathname + location.search + location.hash,
      title,
      content: bodyText,
      referrer: document.referrer || '',
      youtube_title: youtube.youtube_title,
      youtube_channel: youtube.youtube_channel,
      tab_duration_seconds: Number(((Date.now() - pageStartedAt) / 1000).toFixed(1)),
      focus_lost_count: focusLostCount,
      hidden_count: hiddenCount,
      signals: {
        source: 'content_agent_patch',
        page_type: youtube.page_type,
        text_length: bodyText.length,
        title_length: title.length,
        ...extractPageSignals(),
      },
    };
  }

  function buildSignature(context) {
    return [
      context.url,
      context.title,
      context.youtube_title,
      context.youtube_channel,
      Math.round(Number(context.tab_duration_seconds || 0)),
      context.focus_lost_count,
      context.hidden_count,
    ].join('|');
  }

  function sendPageContext(force = false) {
    if (!chrome.runtime?.id) {
      return;
    }

    const context = buildPageContext();
    const signature = buildSignature(context);

    if (!force && signature === lastSignature) {
      return;
    }

    lastSignature = signature;

    try {
      chrome.runtime.sendMessage(
        {
          type: 'PAGE_CONTEXT',
          data: context,
        },
        () => {
          void chrome.runtime.lastError;
        }
      );
    } catch (error) {
      // Ignore message failures during reloads or extension restarts.
    }
  }

  function scheduleSend(delay = 0) {
    if (pendingTimer) {
      clearTimeout(pendingTimer);
    }
    pendingTimer = setTimeout(() => sendPageContext(false), delay);
  }

  function resetForNavigation() {
    pageStartedAt = Date.now();
    lastSignature = '';
    scheduleSend(300);
  }

  try {
    const originalPushState = history.pushState;
    history.pushState = function (...args) {
      const result = originalPushState.apply(this, args);
      resetForNavigation();
      return result;
    };

    const originalReplaceState = history.replaceState;
    history.replaceState = function (...args) {
      const result = originalReplaceState.apply(this, args);
      resetForNavigation();
      return result;
    };
  } catch (error) {
    // History patching can fail in locked-down pages; analysis still works on interval.
  }

  window.addEventListener('popstate', resetForNavigation);
  window.addEventListener('hashchange', resetForNavigation);
  window.addEventListener('blur', () => {
    focusLostCount += 1;
    scheduleSend(0);
  });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      hiddenCount += 1;
      scheduleSend(0);
    }
  });

  window.addEventListener('beforeunload', () => {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
    if (pendingTimer) {
      clearTimeout(pendingTimer);
      pendingTimer = null;
    }
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => scheduleSend(INITIAL_DELAY_MS), { once: true });
  } else {
    scheduleSend(INITIAL_DELAY_MS);
  }

  intervalId = setInterval(() => scheduleSend(0), ANALYZE_INTERVAL_MS);
})();