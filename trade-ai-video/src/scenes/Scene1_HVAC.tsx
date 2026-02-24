import React from "react";
import {
  interpolate,
  useCurrentFrame,
  spring,
  useVideoConfig,
  Easing,
} from "remotion";
import { PhoneScreen } from "../components/PhoneScreen";
import { TextOverlay } from "../components/TextOverlay";

export const Scene1_HVAC: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Slow cinematic pan
  const panX = interpolate(frame, [0, 300], [0, -30], {
    extrapolateRight: "clamp",
  });
  const panY = interpolate(frame, [0, 300], [0, -10], {
    extrapolateRight: "clamp",
  });

  // Worker nod animation at frame ~210
  const nodAngle = interpolate(frame, [200, 215, 230], [0, 8, 0], {
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
        background: "#1a1f2e",
      }}
    >
      {/* Sky background - rooftop setting */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "110%",
          height: "110%",
          transform: `translate(${panX}px, ${panY}px)`,
          background:
            "linear-gradient(180deg, #4a6380 0%, #6b8cad 30%, #8faabe 50%, #c4c8c0 80%, #6a6e66 85%, #4a4e48 100%)",
        }}
      >
        {/* City skyline silhouettes */}
        <div
          style={{
            position: "absolute",
            bottom: "20%",
            left: 0,
            width: "100%",
            height: "15%",
          }}
        >
          {[
            { left: "5%", width: 60, height: 100 },
            { left: "12%", width: 40, height: 140 },
            { left: "18%", width: 80, height: 90 },
            { left: "70%", width: 50, height: 120 },
            { left: "78%", width: 70, height: 80 },
            { left: "88%", width: 45, height: 110 },
          ].map((b, i) => (
            <div
              key={i}
              style={{
                position: "absolute",
                bottom: 0,
                left: b.left,
                width: b.width,
                height: b.height,
                background: `rgba(50,55,65,${0.5 + i * 0.05})`,
                borderRadius: "2px 2px 0 0",
              }}
            />
          ))}
        </div>

        {/* Rooftop surface */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: "-5%",
            width: "120%",
            height: "30%",
            background:
              "linear-gradient(180deg, #5a5e56 0%, #4a4e46 50%, #3a3e36 100%)",
          }}
        />

        {/* HVAC Unit - large commercial box */}
        <div
          style={{
            position: "absolute",
            bottom: "25%",
            right: "15%",
            width: 380,
            height: 260,
            background:
              "linear-gradient(180deg, #7a7e76 0%, #6a6e66 50%, #5a5e56 100%)",
            borderRadius: 6,
            border: "2px solid rgba(0,0,0,0.2)",
            boxShadow: "10px 10px 30px rgba(0,0,0,0.3)",
          }}
        >
          {/* Unit vents */}
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              style={{
                position: "absolute",
                top: 30 + i * 25,
                left: 20,
                width: "80%",
                height: 3,
                background: "rgba(0,0,0,0.25)",
                borderRadius: 1,
              }}
            />
          ))}
          {/* Digital display with fault code */}
          <div
            style={{
              position: "absolute",
              bottom: 20,
              right: 20,
              width: 100,
              height: 45,
              background: "#0a0a0a",
              borderRadius: 4,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              border: "1px solid rgba(255,255,255,0.1)",
            }}
          >
            <span
              style={{
                color: "#ff4444",
                fontSize: 20,
                fontFamily: "monospace",
                fontWeight: 700,
              }}
            >
              E-13
            </span>
          </div>
          {/* Brand label */}
          <div
            style={{
              position: "absolute",
              bottom: 20,
              left: 20,
              padding: "4px 12px",
              background: "rgba(255,255,255,0.1)",
              borderRadius: 3,
            }}
          >
            <span
              style={{
                color: "rgba(255,255,255,0.6)",
                fontSize: 12,
                fontFamily: "SF Pro Display, -apple-system, sans-serif",
                letterSpacing: 2,
                textTransform: "uppercase",
              }}
            >
              HVAC-Pro 9000
            </span>
          </div>
        </div>

        {/* Worker silhouette - crouching */}
        <div
          style={{
            position: "absolute",
            bottom: "24%",
            right: "38%",
            transform: `rotate(${nodAngle}deg)`,
            transformOrigin: "bottom center",
          }}
        >
          {/* Head */}
          <div
            style={{
              width: 50,
              height: 50,
              borderRadius: "50%",
              background: "#2a3040",
              margin: "0 auto 2px",
              position: "relative",
            }}
          >
            {/* Hard hat */}
            <div
              style={{
                position: "absolute",
                top: -5,
                left: -4,
                width: 58,
                height: 30,
                borderRadius: "30px 30px 0 0",
                background: "#e0a020",
              }}
            />
          </div>
          {/* Torso - crouching position */}
          <div
            style={{
              width: 70,
              height: 80,
              background: "#2a3040",
              borderRadius: "8px 8px 0 0",
              margin: "0 auto",
              position: "relative",
            }}
          >
            {/* High-vis vest stripe */}
            <div
              style={{
                position: "absolute",
                top: 10,
                left: 5,
                width: 60,
                height: 6,
                background: "#e0c020",
                borderRadius: 2,
              }}
            />
            <div
              style={{
                position: "absolute",
                top: 22,
                left: 5,
                width: 60,
                height: 6,
                background: "#e0c020",
                borderRadius: 2,
              }}
            />
          </div>
          {/* Arm holding phone */}
          <div
            style={{
              position: "absolute",
              top: 60,
              right: -80,
              width: 80,
              height: 20,
              background: "#2a3040",
              borderRadius: 10,
              transform: "rotate(-15deg)",
            }}
          />
          {/* Legs - crouching */}
          <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
            <div
              style={{
                width: 30,
                height: 50,
                background: "#252a38",
                borderRadius: "0 0 6px 6px",
                transform: "rotate(-10deg)",
              }}
            />
            <div
              style={{
                width: 30,
                height: 50,
                background: "#252a38",
                borderRadius: "0 0 6px 6px",
                transform: "rotate(10deg)",
              }}
            />
          </div>
        </div>

        {/* Phone in hand */}
        <div
          style={{
            position: "absolute",
            bottom: "36%",
            right: "25%",
          }}
        >
          <PhoneScreen
            startFrame={30}
            showResponse={true}
            responseStartFrame={150}
            questionText="What's causing fault code 13 on this unit?"
            responseText="Fault code E-13 typically indicates a refrigerant pressure sensor failure. Check the high-pressure switch wiring and sensor connection at the condenser coil."
          />
        </div>

        {/* Toolbox on ground */}
        <div
          style={{
            position: "absolute",
            bottom: "19%",
            right: "42%",
            width: 80,
            height: 40,
            background: "#cc3333",
            borderRadius: 4,
            border: "2px solid rgba(0,0,0,0.2)",
          }}
        >
          <div
            style={{
              width: 40,
              height: 8,
              background: "#999",
              borderRadius: 4,
              margin: "4px auto",
            }}
          />
        </div>

        {/* Subtle sun/warm light source */}
        <div
          style={{
            position: "absolute",
            top: "5%",
            right: "20%",
            width: 300,
            height: 300,
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(255,200,100,0.15) 0%, transparent 70%)",
          }}
        />
      </div>

      {/* Text overlay */}
      <TextOverlay
        text="What's causing fault code 13 on this unit?"
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
            HVAC Diagnostics
          </span>
        </div>
      </div>
    </div>
  );
};
