import React from "react";
import {
  interpolate,
  useCurrentFrame,
  spring,
  useVideoConfig,
} from "remotion";

export const TextOverlay: React.FC<{
  text: string;
  startFrame: number;
  durationFrames: number;
  position?: "bottom-left" | "bottom-center" | "center";
  style?: "question" | "label";
}> = ({
  text,
  startFrame,
  durationFrames,
  position = "bottom-left",
  style = "question",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const localFrame = frame - startFrame;
  if (localFrame < 0 || localFrame > durationFrames) return null;

  const fadeIn = spring({
    frame: localFrame,
    fps,
    config: { damping: 20, stiffness: 100 },
  });

  const fadeOut = interpolate(
    localFrame,
    [durationFrames - 20, durationFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const slideY = interpolate(fadeIn, [0, 1], [20, 0]);
  const opacity = Math.min(fadeIn, fadeOut);

  const positionStyle: React.CSSProperties =
    position === "bottom-left"
      ? { bottom: 120, left: 100 }
      : position === "bottom-center"
        ? { bottom: 120, left: "50%", transform: `translateX(-50%) translateY(${slideY}px)` }
        : { top: "50%", left: "50%", transform: `translate(-50%, -50%) translateY(${slideY}px)` };

  if (position === "bottom-left") {
    positionStyle.transform = `translateY(${slideY}px)`;
  }

  return (
    <div
      style={{
        position: "absolute",
        ...positionStyle,
        opacity,
        zIndex: 10,
      }}
    >
      {style === "question" ? (
        <div
          style={{
            background: "rgba(0, 0, 0, 0.65)",
            backdropFilter: "blur(20px)",
            borderRadius: 16,
            padding: "20px 32px",
            border: "1px solid rgba(255,255,255,0.15)",
            maxWidth: 700,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              marginBottom: 8,
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: "#4ADE80",
              }}
            />
            <span
              style={{
                color: "rgba(255,255,255,0.5)",
                fontSize: 16,
                fontFamily: "SF Pro Display, -apple-system, sans-serif",
                fontWeight: 500,
                letterSpacing: 1.5,
                textTransform: "uppercase",
              }}
            >
              Voice Input
            </span>
          </div>
          <div
            style={{
              color: "#fff",
              fontSize: 28,
              fontFamily: "SF Pro Display, -apple-system, sans-serif",
              fontWeight: 400,
              lineHeight: 1.4,
              letterSpacing: -0.3,
            }}
          >
            "{text}"
          </div>
        </div>
      ) : (
        <div
          style={{
            color: "rgba(255,255,255,0.9)",
            fontSize: 22,
            fontFamily: "SF Pro Display, -apple-system, sans-serif",
            fontWeight: 500,
            letterSpacing: 1,
          }}
        >
          {text}
        </div>
      )}
    </div>
  );
};
