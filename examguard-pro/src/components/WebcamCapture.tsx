import { useCallback, useEffect, useRef, useState } from "react";

type CaptureMode = "webcam" | "screen";

interface WebcamCaptureProps {
  onCapture?: (imageSrc: string) => void;
  onUserMedia?: () => void;
  width?: number;
  height?: number;
  allowScreenShare?: boolean;
}

export function WebcamCapture({
  onCapture,
  onUserMedia,
  width = 320,
  height = 240,
  allowScreenShare = false,
}: WebcamCaptureProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const webcamStreamRef = useRef<MediaStream | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  const activeModeRef = useRef<CaptureMode>("webcam");
  const requestLockRef = useRef(false);

  const [activeMode, setActiveMode] = useState<CaptureMode>("webcam");
  const [isReady, setIsReady] = useState(false);
  const [isRequesting, setIsRequesting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const clearVideoElement = useCallback(() => {
    const video = videoRef.current;
    if (video) {
      video.srcObject = null;
    }
    setIsReady(false);
  }, []);

  const attachStream = useCallback(async (stream: MediaStream, mode: CaptureMode) => {
    const video = videoRef.current;
    if (!video) return;

    video.srcObject = stream;
    video.muted = true;
    video.playsInline = true;
    activeModeRef.current = mode;
    setActiveMode(mode);
    setIsReady(true);
    setErrorMessage(null);

    try {
      await video.play();
    } catch {
      // Autoplay can race with stream assignment; the stream is still attached.
    }
  }, []);

  const stopStream = useCallback((stream: MediaStream | null) => {
    if (!stream) return;
    stream.getTracks().forEach((track) => track.stop());
  }, []);

  const startWebcamCapture = useCallback(async () => {
    if (requestLockRef.current) return;

    requestLockRef.current = true;
    setIsRequesting(true);

    try {
      if (!webcamStreamRef.current) {
        webcamStreamRef.current = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: width },
            height: { ideal: height },
            facingMode: "user",
            frameRate: { ideal: 15 },
          },
          audio: false,
        });

        const [track] = webcamStreamRef.current.getVideoTracks();
        if (track) {
          track.onended = () => {
            webcamStreamRef.current = null;
            if (activeModeRef.current === "webcam") {
              if (allowScreenShare && screenStreamRef.current) {
                void attachStream(screenStreamRef.current, "screen");
              } else {
                clearVideoElement();
              }
            }
          };
        }
      }

      await attachStream(webcamStreamRef.current, "webcam");
      onUserMedia?.();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Permission denied");
      console.error("Webcam error:", error);
    } finally {
      requestLockRef.current = false;
      setIsRequesting(false);
    }
  }, [allowScreenShare, attachStream, clearVideoElement, height, onUserMedia, width]);

  const startScreenShare = useCallback(async () => {
    if (!allowScreenShare || requestLockRef.current) return;

    requestLockRef.current = true;
    setIsRequesting(true);

    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          cursor: "always",
          displaySurface: "monitor",
          width: { ideal: width },
          height: { ideal: height },
        },
        audio: false,
      });

      screenStreamRef.current = stream;
      const [track] = stream.getVideoTracks();
      if (track) {
        track.onended = () => {
          screenStreamRef.current = null;
          if (activeModeRef.current === "screen") {
            if (webcamStreamRef.current) {
              void attachStream(webcamStreamRef.current, "webcam");
              onUserMedia?.();
            } else {
              clearVideoElement();
            }
          }
        };
      }

      await attachStream(stream, "screen");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Screen sharing denied");
      console.error("Screen share error:", error);
    } finally {
      requestLockRef.current = false;
      setIsRequesting(false);
    }
  }, [allowScreenShare, attachStream, clearVideoElement, height, onUserMedia, width]);

  const capture = useCallback(() => {
    const video = videoRef.current;
    if (!video || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      return null;
    }

    const captureWidth = video.videoWidth || width;
    const captureHeight = video.videoHeight || height;
    const canvas = document.createElement("canvas");
    canvas.width = captureWidth;
    canvas.height = captureHeight;

    const context = canvas.getContext("2d");
    if (!context) return null;

    if (activeModeRef.current === "webcam") {
      context.save();
      context.translate(captureWidth, 0);
      context.scale(-1, 1);
      context.drawImage(video, 0, 0, captureWidth, captureHeight);
      context.restore();
    } else {
      context.drawImage(video, 0, 0, captureWidth, captureHeight);
    }

    return canvas.toDataURL("image/jpeg", 0.6);
  }, [height, width]);

  const handleCapture = useCallback(() => {
    const imageSrc = capture();
    if (imageSrc && onCapture) {
      onCapture(imageSrc);
    }
    return imageSrc;
  }, [capture, onCapture]);

  useEffect(() => {
    void startWebcamCapture();

    return () => {
      requestLockRef.current = false;
      stopStream(webcamStreamRef.current);
      stopStream(screenStreamRef.current);
      webcamStreamRef.current = null;
      screenStreamRef.current = null;
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, [startWebcamCapture, stopStream]);

  return (
    <div className="relative w-full">
      <div className="relative overflow-hidden rounded-lg bg-slate-900">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          className="block w-full bg-slate-900"
          style={{
            width,
            height,
            objectFit: "cover",
            transform: activeMode === "webcam" ? "scaleX(-1)" : "none",
          }}
        />

        {!isReady && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-slate-950/80 text-slate-200">
            <div className="text-sm font-medium">
              {isRequesting ? "Starting camera..." : "Waiting for camera access"}
            </div>
            <div className="text-xs text-slate-400">
              {errorMessage || "Allow access to continue"}
            </div>
          </div>
        )}

        {isReady && (
          <button
            type="button"
            onClick={handleCapture}
            className="absolute bottom-2 left-1/2 -translate-x-1/2 rounded-full bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            Capture
          </button>
        )}
      </div>

      {allowScreenShare && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void startWebcamCapture()}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
              activeMode === "webcam"
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            Camera
          </button>
          <button
            type="button"
            onClick={() => void startScreenShare()}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
              activeMode === "screen"
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            Share Screen
          </button>
        </div>
      )}
    </div>
  );
}

export default WebcamCapture;
