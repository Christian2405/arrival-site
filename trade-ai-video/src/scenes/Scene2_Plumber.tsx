import React from "react";
import {
  interpolate,
  useCurrentFrame,
  spring,
  useVideoConfig,
} from "remotion";
import { PhoneScreen } from "../components/PhoneScreen";
import { TextOverlay } from "../components/TextOverlay";

export const Scene2_Plumber: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Subtle camera drift
  const driftX = interpolate(frame, [0, 300], [10, -15], {
    extrapolateRight: "clamp",
  });

  // Arm adjustment movement at ~frame 210
  const armMove = interpolate(frame, [200, 220, 240], [0, -15, -10], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        overflow: "hidden",
        background: "#1e1a16",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "110%",
          height: "110%",
          transform: `translate(${driftX}px, 0)`,
        }}
      >
        {/* Kitchen background - upper cabinets visible */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "25%",
            background:
              "linear-gradient(180deg, #2a2520 0%, #342e28 100%)",
          }}
        />

        {/* Counter/cabinet frame - we're looking from under the sink */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            background:
              "linear-gradient(180deg, #3a3430 0%, #2a2420 30%, #1e1a16 100%)",
          }}
        />

        {/* Cabinet opening - dark arch framing the under-sink area */}
        <div
          style={{
            position: "absolute",
            top: "5%",
            left: "8%",
            width: "84%",
            height: "90%",
            background: "#0d0a08",
            borderRadius: "8px 8px 0 0",
            border: "4px solid #4a4038",
            borderBottom: "none",
          }}
        >
          {/* Under-sink interior */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              background:
                "radial-gradient(ellipse at 40% 30%, #2a2218 0%, #0d0a08 70%)",
            }}
          />

          {/* Pipes */}
          {/* Main drain pipe - vertical */}
          <div
            style={{
              position: "absolute",
              top: "10%",
              left: "45%",
              width: 35,
              height: "60%",
              background:
                "linear-gradient(90deg, #8a8a8a, #b0b0b0, #8a8a8a)",
              borderRadius: 4,
            }}
          />
          {/* P-trap curve */}
          <div
            style={{
              position: "absolute",
              top: "62%",
              left: "35%",
              width: 120,
              height: 60,
              borderRadius: "0 0 60px 60px",
              border: "18px solid #9a9a9a",
              borderTop: "none",
              background: "transparent",
            }}
          />
          {/* Horizontal drain pipe going into wall */}
          <div
            style={{
              position: "absolute",
              top: "55%",
              left: "60%",
              width: "45%",
              height: 32,
              background:
                "linear-gradient(90deg, #8a8a8a, #a0a0a0, #8a8a8a)",
              borderRadius: "4px 0 0 4px",
              transform: `translateY(${armMove * 0.3}px)`,
            }}
          />
          {/* Water supply lines */}
          <div
            style={{
              position: "absolute",
              top: "5%",
              left: "20%",
              width: 14,
              height: "50%",
              background:
                "linear-gradient(90deg, #4488cc, #66aaee, #4488cc)",
              borderRadius: 3,
            }}
          />
          <div
            style={{
              position: "absolute",
              top: "5%",
              left: "72%",
              width: 14,
              height: "45%",
              background:
                "linear-gradient(90deg, #cc4444, #ee6666, #cc4444)",
              borderRadius: 3,
            }}
          />
          {/* Shut-off valves */}
          <div
            style={{
              position: "absolute",
              top: "42%",
              left: "17%",
              width: 22,
              height: 22,
              borderRadius: "50%",
              background: "#4488cc",
              border: "2px solid #2266aa",
            }}
          />
          <div
            style={{
              position: "absolute",
              top: "38%",
              left: "69%",
              width: 22,
              height: 22,
              borderRadius: "50%",
              background: "#cc4444",
              border: "2px solid #aa2222",
            }}
          />

          {/* Worker - female plumber, upper body visible from below */}
          <div
            style={{
              position: "absolute",
              bottom: "8%",
              left: "8%",
              transform: `translateY(${armMove * 0.2}px)`,
            }}
          >
            {/* Head with ponytail */}
            <div style={{ position: "relative" }}>
              <div
                style={{
                  width: 60,
                  height: 60,
                  borderRadius: "50%",
                  background: "#3a2a20",
                  margin: "0 auto",
                }}
              />
              {/* Hair / ponytail */}
              <div
                style={{
                  position: "absolute",
                  top: 10,
                  right: -20,
                  width: 40,
                  height: 16,
                  background: "#2a1a10",
                  borderRadius: "0 10px 10px 0",
                }}
              />
              {/* Earbud */}
              <div
                style={{
                  position: "absolute",
                  top: 28,
                  left: 6,
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: "#fff",
                  boxShadow: "0 0 6px rgba(255,255,255,0.3)",
                }}
              />
            </div>
            {/* Torso */}
            <div
              style={{
                width: 80,
                height: 100,
                background: "#2a3848",
                borderRadius: "8px 8px 0 0",
                margin: "2px auto 0",
                position: "relative",
              }}
            >
              {/* Work shirt collar */}
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: "50%",
                  transform: "translateX(-50%)",
                  width: 30,
                  height: 15,
                  background: "#3a4858",
                  borderRadius: "0 0 10px 10px",
                }}
              />
            </div>
            {/* Arms */}
            <div
              style={{
                position: "absolute",
                top: 80,
                right: -70,
                width: 80,
                height: 22,
                background: "#2a3848",
                borderRadius: 12,
                transform: `rotate(-20deg) translateY(${armMove}px)`,
              }}
            />
            <div
              style={{
                position: "absolute",
                top: 90,
                right: -100,
                width: 30,
                height: 30,
                background: "#4a3a30",
                borderRadius: "50%",
                transform: `translateY(${armMove}px)`,
              }}
            />
          </div>

          {/* Phone propped against wall */}
          <div
            style={{
              position: "absolute",
              top: "15%",
              right: "8%",
              transform: "rotate(5deg)",
            }}
          >
            <PhoneScreen
              startFrame={20}
              showResponse={true}
              responseStartFrame={140}
              questionText="How do I properly slope this drain for a kitchen island?"
              responseText="For a kitchen island drain, maintain a 1/4 inch slope per foot toward the main stack. Use a level on the horizontal run and adjust hangers accordingly."
            />
          </div>

          {/* Work light / flashlight glow */}
          <div
            style={{
              position: "absolute",
              top: "20%",
              left: "30%",
              width: 200,
              height: 200,
              borderRadius: "50%",
              background:
                "radial-gradient(circle, rgba(255,220,150,0.15) 0%, transparent 70%)",
            }}
          />
        </div>
      </div>

      {/* Text overlay */}
      <TextOverlay
        text="How do I properly slope this drain for a kitchen island?"
        startFrame={50}
        durationFrames={210}
      />

      {/* Scene label */}
      <div
        style={{
          position: "absolute",
          top: 40,
          left: 60,
          opacity: interpolate(frame, [10, 30], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <div
            style={{
              width: 30,
              height: 2,
              background: "rgba(255,255,255,0.4)",
            }}
          />
          <span
            style={{
              color: "rgba(255,255,255,0.5)",
              fontSize: 15,
              fontFamily: "SF Pro Display, -apple-system, sans-serif",
              fontWeight: 500,
              letterSpacing: 3,
              textTransform: "uppercase",
            }}
          >
            Plumbing
          </span>
        </div>
      </div>
    </div>
  );
};
