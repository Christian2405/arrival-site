import React from "react";
import {
  interpolate,
  useCurrentFrame,
  spring,
  useVideoConfig,
} from "remotion";
import { PhoneScreen } from "../components/PhoneScreen";
import { TextOverlay } from "../components/TextOverlay";

export const Scene3_Apprentice: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Slow zoom in toward the equipment
  const zoom = interpolate(frame, [0, 300], [1, 1.06], {
    extrapolateRight: "clamp",
  });

  // Equipment start-up: lights turn on at ~240
  const startUpProgress = interpolate(frame, [230, 260], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Satisfaction moment - slight posture shift
  const satisfactionShift = interpolate(frame, [260, 275], [0, -5], {
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
        background: "#14161e",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          transform: `scale(${zoom})`,
          transformOrigin: "60% 50%",
        }}
      >
        {/* Mechanical room background */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            background:
              "linear-gradient(180deg, #1a1e28 0%, #161a22 50%, #12141c 100%)",
          }}
        />

        {/* Concrete walls */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            background:
              "linear-gradient(90deg, #1e222c 0%, #1a1e26 10%, #161a22 50%, #1a1e26 90%, #1e222c 100%)",
          }}
        />

        {/* Pipes along ceiling */}
        {[
          { top: "4%", color: "#cc4444", height: 20 },
          { top: "8%", color: "#4488cc", height: 16 },
          { top: "12%", color: "#888", height: 24 },
        ].map((pipe, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              top: pipe.top,
              left: 0,
              width: "100%",
              height: pipe.height,
              background: `linear-gradient(180deg, ${pipe.color}, ${pipe.color}aa, ${pipe.color})`,
              boxShadow: `0 4px 8px rgba(0,0,0,0.3)`,
            }}
          />
        ))}

        {/* Main equipment panel - large industrial unit */}
        <div
          style={{
            position: "absolute",
            top: "20%",
            right: "10%",
            width: 500,
            height: 500,
            background:
              "linear-gradient(180deg, #3a3e48 0%, #2a2e38 50%, #22262e 100%)",
            borderRadius: 6,
            border: "3px solid #4a4e58",
            boxShadow: "0 10px 40px rgba(0,0,0,0.5)",
          }}
        >
          {/* Control panel section */}
          <div
            style={{
              position: "absolute",
              top: 20,
              left: 20,
              width: "calc(100% - 40px)",
              height: 120,
              background: "#1a1e28",
              borderRadius: 4,
              border: "1px solid #3a3e48",
              padding: 15,
              display: "flex",
              gap: 15,
              alignItems: "center",
            }}
          >
            {/* Status lights */}
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {["POWER", "RUN", "FAULT", "COMM"].map((label, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <div
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: "50%",
                      background:
                        startUpProgress > 0
                          ? i === 2
                            ? "#333"
                            : ["#4ADE80", "#4ADE80", "#ff4444", "#22D3EE"][i]
                          : i === 0
                            ? "#ff4444"
                            : "#333",
                      boxShadow:
                        startUpProgress > 0 && i !== 2
                          ? `0 0 8px ${["#4ADE80", "#4ADE80", "transparent", "#22D3EE"][i]}`
                          : "none",
                      transition: "all 0.5s",
                    }}
                  />
                  <span
                    style={{
                      color: "rgba(255,255,255,0.4)",
                      fontSize: 10,
                      fontFamily: "monospace",
                      letterSpacing: 1,
                    }}
                  >
                    {label}
                  </span>
                </div>
              ))}
            </div>

            {/* Digital readout */}
            <div
              style={{
                flex: 1,
                height: "100%",
                background: "#0a0c14",
                borderRadius: 4,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: "1px solid #2a2e38",
              }}
            >
              <span
                style={{
                  color: startUpProgress > 0 ? "#4ADE80" : "#ff4444",
                  fontSize: 24,
                  fontFamily: "monospace",
                  fontWeight: 700,
                }}
              >
                {startUpProgress > 0 ? "RUNNING" : "STANDBY"}
              </span>
            </div>
          </div>

          {/* Breakers / switches grid */}
          <div
            style={{
              position: "absolute",
              top: 160,
              left: 20,
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: 12,
              width: "calc(100% - 40px)",
            }}
          >
            {Array.from({ length: 12 }).map((_, i) => (
              <div
                key={i}
                style={{
                  height: 50,
                  background: "#22262e",
                  borderRadius: 4,
                  border: "1px solid #3a3e48",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <div
                  style={{
                    width: 16,
                    height: 24,
                    background: i < 3 && startUpProgress > 0 ? "#4a5060" : "#2a2e38",
                    borderRadius: 3,
                    border: "1px solid #4a4e58",
                  }}
                />
              </div>
            ))}
          </div>

          {/* Brand plate */}
          <div
            style={{
              position: "absolute",
              bottom: 20,
              left: "50%",
              transform: "translateX(-50%)",
              padding: "8px 24px",
              background: "rgba(255,255,255,0.05)",
              borderRadius: 4,
              border: "1px solid rgba(255,255,255,0.1)",
            }}
          >
            <span
              style={{
                color: "rgba(255,255,255,0.4)",
                fontSize: 14,
                fontFamily: "SF Pro Display, -apple-system, sans-serif",
                letterSpacing: 4,
                textTransform: "uppercase",
              }}
            >
              MechControl 3200
            </span>
          </div>
        </div>

        {/* Apprentice figure - young, standing, slightly uncertain posture initially */}
        <div
          style={{
            position: "absolute",
            bottom: "8%",
            left: "18%",
            transform: `translateY(${satisfactionShift}px)`,
          }}
        >
          {/* Head */}
          <div
            style={{
              width: 55,
              height: 55,
              borderRadius: "50%",
              background: "#3a2e24",
              margin: "0 auto 2px",
              position: "relative",
            }}
          >
            {/* Short hair */}
            <div
              style={{
                position: "absolute",
                top: -3,
                left: 2,
                width: 51,
                height: 30,
                borderRadius: "28px 28px 0 0",
                background: "#2a1e14",
              }}
            />
            {/* Earbud */}
            <div
              style={{
                position: "absolute",
                top: 25,
                right: -2,
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: "#fff",
                boxShadow: "0 0 6px rgba(255,255,255,0.3)",
              }}
            />
            {/* Slight smile at end */}
            {satisfactionShift < -2 && (
              <div
                style={{
                  position: "absolute",
                  bottom: 12,
                  left: "50%",
                  transform: "translateX(-50%)",
                  width: 16,
                  height: 6,
                  borderRadius: "0 0 8px 8px",
                  border: "2px solid rgba(255,255,255,0.2)",
                  borderTop: "none",
                }}
              />
            )}
          </div>
          {/* Torso */}
          <div
            style={{
              width: 80,
              height: 120,
              background: "#2a4040",
              borderRadius: "8px 8px 0 0",
              margin: "0 auto",
              position: "relative",
            }}
          >
            {/* Company logo patch */}
            <div
              style={{
                position: "absolute",
                top: 15,
                left: 12,
                width: 30,
                height: 18,
                background: "rgba(255,255,255,0.1)",
                borderRadius: 3,
              }}
            />
          </div>
          {/* Arm holding phone up */}
          <div
            style={{
              position: "absolute",
              top: 60,
              right: -90,
              width: 100,
              height: 22,
              background: "#2a4040",
              borderRadius: 12,
              transform: "rotate(-40deg)",
            }}
          />
          {/* Legs */}
          <div style={{ display: "flex", gap: 6, justifyContent: "center" }}>
            <div
              style={{
                width: 32,
                height: 100,
                background: "#252830",
                borderRadius: "0 0 6px 6px",
              }}
            />
            <div
              style={{
                width: 32,
                height: 100,
                background: "#252830",
                borderRadius: "0 0 6px 6px",
              }}
            />
          </div>
          {/* Work boots */}
          <div style={{ display: "flex", gap: 6, justifyContent: "center" }}>
            <div
              style={{
                width: 38,
                height: 18,
                background: "#3a2a1a",
                borderRadius: "4px 4px 6px 6px",
              }}
            />
            <div
              style={{
                width: 38,
                height: 18,
                background: "#3a2a1a",
                borderRadius: "4px 4px 6px 6px",
              }}
            />
          </div>
        </div>

        {/* Phone held up */}
        <div
          style={{
            position: "absolute",
            bottom: "40%",
            left: "30%",
          }}
        >
          <PhoneScreen
            startFrame={40}
            showResponse={true}
            responseStartFrame={120}
            questionText="Can you walk me through this start-up procedure?"
            responseText="Step 1: Verify all breakers are in OFF position. Step 2: Enable main power switch. Step 3: Set mode selector to AUTO. Step 4: Press and hold START for 3 seconds..."
          />
        </div>

        {/* Fluorescent ceiling light */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: "40%",
            width: 200,
            height: 8,
            background: "rgba(200,220,255,0.6)",
            borderRadius: 4,
            boxShadow: "0 0 60px rgba(200,220,255,0.15)",
          }}
        />

        {/* Equipment start-up glow effect */}
        {startUpProgress > 0 && (
          <div
            style={{
              position: "absolute",
              top: "30%",
              right: "20%",
              width: 300,
              height: 300,
              borderRadius: "50%",
              background: `radial-gradient(circle, rgba(74,222,128,${0.08 * startUpProgress}) 0%, transparent 70%)`,
            }}
          />
        )}

        {/* Floor */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            width: "100%",
            height: "12%",
            background:
              "linear-gradient(180deg, #1a1c24 0%, #16181e 100%)",
          }}
        />
      </div>

      {/* Text overlay */}
      <TextOverlay
        text="Can you walk me through this start-up procedure?"
        startFrame={60}
        durationFrames={200}
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
            Mechanical Systems
          </span>
        </div>
      </div>
    </div>
  );
};
