import React from "react";
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Scene1_HVAC } from "./scenes/Scene1_HVAC";
import { Scene2_Plumber } from "./scenes/Scene2_Plumber";
import { Scene3_Apprentice } from "./scenes/Scene3_Apprentice";
import { ColorGrade } from "./components/ColorGrade";

const SCENE_DURATION = 300; // 10 seconds at 30fps
const TRANSITION_OVERLAP = 20; // ~0.67 second cross-dissolve
const TOTAL_FRAMES = 900; // 30 seconds

export const TradeAIVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Scene timing with overlapping transitions
  const scene1Start = 0;
  const scene1End = SCENE_DURATION;
  const scene2Start = SCENE_DURATION - TRANSITION_OVERLAP;
  const scene2End = SCENE_DURATION * 2 - TRANSITION_OVERLAP;
  const scene3Start = (SCENE_DURATION - TRANSITION_OVERLAP) * 2;
  const scene3End = TOTAL_FRAMES;

  // Scene opacities with cross-dissolve
  const scene1Opacity = interpolate(
    frame,
    [scene1End - TRANSITION_OVERLAP, scene1End],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const scene2Opacity =
    interpolate(
      frame,
      [scene2Start, scene2Start + TRANSITION_OVERLAP],
      [0, 1],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    ) *
    interpolate(
      frame,
      [scene2End - TRANSITION_OVERLAP, scene2End],
      [1, 0],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );

  const scene3OpacityIn = interpolate(
    frame,
    [scene3Start, scene3Start + TRANSITION_OVERLAP],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Seamless loop: fade out at end to match scene 1 start
  const loopFadeOut = interpolate(
    frame,
    [TOTAL_FRAMES - TRANSITION_OVERLAP, TOTAL_FRAMES],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const scene3Opacity = scene3OpacityIn * loopFadeOut;

  // Loop bridge: scene 1 fades back in at the very end for seamless loop
  const loopBridgeOpacity = interpolate(
    frame,
    [TOTAL_FRAMES - TRANSITION_OVERLAP, TOTAL_FRAMES],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <ColorGrade>
        <AbsoluteFill>
          {/* Scene 1 */}
          {frame <= scene1End && (
            <AbsoluteFill style={{ opacity: scene1Opacity }}>
              <Sequence from={scene1Start} durationInFrames={SCENE_DURATION}>
                <Scene1_HVAC />
              </Sequence>
            </AbsoluteFill>
          )}

          {/* Scene 2 */}
          {frame >= scene2Start && frame <= scene2End && (
            <AbsoluteFill style={{ opacity: scene2Opacity }}>
              <Sequence from={scene2Start} durationInFrames={SCENE_DURATION}>
                <Scene2_Plumber />
              </Sequence>
            </AbsoluteFill>
          )}

          {/* Scene 3 */}
          {frame >= scene3Start && (
            <AbsoluteFill style={{ opacity: scene3Opacity }}>
              <Sequence
                from={scene3Start}
                durationInFrames={TOTAL_FRAMES - scene3Start}
              >
                <Scene3_Apprentice />
              </Sequence>
            </AbsoluteFill>
          )}

          {/* Loop bridge: Scene 1 reappears at end for seamless loop */}
          {frame >= TOTAL_FRAMES - TRANSITION_OVERLAP && (
            <AbsoluteFill style={{ opacity: loopBridgeOpacity }}>
              <Scene1_HVAC />
            </AbsoluteFill>
          )}
        </AbsoluteFill>

        {/* Bottom branding bar */}
        <div
          style={{
            position: "absolute",
            bottom: 30,
            right: 60,
            display: "flex",
            alignItems: "center",
            gap: 10,
            opacity: 0.4,
          }}
        >
          <div
            style={{
              width: 24,
              height: 24,
              borderRadius: 6,
              background: "linear-gradient(135deg, #4ADE80, #22D3EE)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <span style={{ fontSize: 11, color: "#000", fontWeight: 700 }}>
              AI
            </span>
          </div>
          <span
            style={{
              color: "rgba(255,255,255,0.6)",
              fontSize: 16,
              fontFamily: "SF Pro Display, -apple-system, sans-serif",
              fontWeight: 500,
              letterSpacing: 1.5,
            }}
          >
            TradeAssist
          </span>
        </div>

        {/* Progress indicator dots */}
        <div
          style={{
            position: "absolute",
            bottom: 36,
            left: "50%",
            transform: "translateX(-50%)",
            display: "flex",
            gap: 10,
          }}
        >
          {[0, 1, 2].map((i) => {
            const isActive =
              (i === 0 && frame < scene2Start) ||
              (i === 1 && frame >= scene2Start && frame < scene3Start) ||
              (i === 2 && frame >= scene3Start);
            return (
              <div
                key={i}
                style={{
                  width: isActive ? 24 : 8,
                  height: 8,
                  borderRadius: 4,
                  background: isActive
                    ? "rgba(74,222,128,0.7)"
                    : "rgba(255,255,255,0.2)",
                  transition: "all 0.3s",
                }}
              />
            );
          })}
        </div>
      </ColorGrade>
    </AbsoluteFill>
  );
};
