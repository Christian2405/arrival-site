import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

export const CrossDissolve: React.FC<{
  children: React.ReactNode;
  startFrame: number;
  endFrame: number;
  direction: "in" | "out";
}> = ({ children, startFrame, endFrame, direction }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(
    frame,
    [startFrame, endFrame],
    direction === "in" ? [0, 1] : [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const scale = interpolate(
    frame,
    [startFrame, endFrame],
    direction === "in" ? [1.02, 1] : [1, 0.98],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        opacity,
        transform: `scale(${scale})`,
      }}
    >
      {children}
    </div>
  );
};
