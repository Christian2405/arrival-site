import React from "react";
import { interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";

export const PhoneScreen: React.FC<{
  startFrame: number;
  showResponse?: boolean;
  responseStartFrame?: number;
  responseText?: string;
  questionText?: string;
}> = ({
  startFrame,
  showResponse = false,
  responseStartFrame = 0,
  responseText = "",
  questionText = "",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const localFrame = frame - startFrame;
  if (localFrame < 0) return null;

  const phoneAppear = spring({
    frame: localFrame,
    fps,
    config: { damping: 15, stiffness: 80 },
  });

  const responseLocal = frame - responseStartFrame;
  const responseAppear =
    showResponse && responseLocal > 0
      ? spring({
          frame: responseLocal,
          fps,
          config: { damping: 20, stiffness: 100 },
        })
      : 0;

  return (
    <div
      style={{
        width: 220,
        height: 440,
        borderRadius: 30,
        background: "#1a1a2e",
        border: "3px solid rgba(255,255,255,0.2)",
        overflow: "hidden",
        opacity: phoneAppear,
        transform: `scale(${interpolate(phoneAppear, [0, 1], [0.8, 1])})`,
        boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Status bar */}
      <div
        style={{
          height: 36,
          background: "#0d0d1a",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 4,
        }}
      >
        <div
          style={{
            width: 50,
            height: 18,
            borderRadius: 10,
            background: "#000",
          }}
        />
      </div>

      {/* App header */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: 8,
            background: "linear-gradient(135deg, #4ADE80, #22D3EE)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span style={{ fontSize: 14, color: "#000", fontWeight: 700 }}>AI</span>
        </div>
        <span
          style={{
            color: "#fff",
            fontSize: 14,
            fontFamily: "SF Pro Display, -apple-system, sans-serif",
            fontWeight: 600,
          }}
        >
          TradeAssist
        </span>
        <div
          style={{
            marginLeft: "auto",
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: "#4ADE80",
          }}
        />
      </div>

      {/* Chat area */}
      <div
        style={{
          flex: 1,
          padding: 12,
          display: "flex",
          flexDirection: "column",
          gap: 10,
          overflow: "hidden",
        }}
      >
        {questionText && (
          <div
            style={{
              alignSelf: "flex-end",
              background: "#2563EB",
              borderRadius: "14px 14px 4px 14px",
              padding: "8px 12px",
              maxWidth: "85%",
            }}
          >
            <span
              style={{
                color: "#fff",
                fontSize: 11,
                fontFamily: "SF Pro Display, -apple-system, sans-serif",
                lineHeight: 1.3,
              }}
            >
              {questionText}
            </span>
          </div>
        )}

        {responseAppear > 0 && (
          <div
            style={{
              alignSelf: "flex-start",
              background: "rgba(255,255,255,0.08)",
              borderRadius: "14px 14px 14px 4px",
              padding: "8px 12px",
              maxWidth: "85%",
              opacity: responseAppear,
              transform: `translateY(${interpolate(responseAppear, [0, 1], [8, 0])}px)`,
            }}
          >
            <span
              style={{
                color: "rgba(255,255,255,0.9)",
                fontSize: 10,
                fontFamily: "SF Pro Display, -apple-system, sans-serif",
                lineHeight: 1.4,
              }}
            >
              {responseText}
            </span>
          </div>
        )}
      </div>

      {/* Push-to-talk button */}
      <div
        style={{
          padding: "10px 16px 20px",
          display: "flex",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            width: 50,
            height: 50,
            borderRadius: "50%",
            background:
              localFrame > 10
                ? "linear-gradient(135deg, #4ADE80, #22D3EE)"
                : "rgba(255,255,255,0.1)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "background 0.3s",
            boxShadow:
              localFrame > 10 ? "0 0 20px rgba(74,222,128,0.4)" : "none",
          }}
        >
          <div
            style={{
              width: 0,
              height: 0,
              borderLeft: "8px solid transparent",
              borderRight: "8px solid transparent",
              borderBottom: localFrame > 10 ? "none" : "14px solid rgba(255,255,255,0.6)",
            }}
          />
          {localFrame > 10 && (
            <div style={{ display: "flex", gap: 2, alignItems: "center" }}>
              {[0, 1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  style={{
                    width: 3,
                    height:
                      8 +
                      Math.sin((localFrame + i * 8) * 0.3) * 8,
                    background: "#000",
                    borderRadius: 2,
                  }}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
