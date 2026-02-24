import React from "react";

export const ColorGrade: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        filter: "saturate(0.7) contrast(1.08)",
      }}
    >
      {children}
      {/* Warm highlight overlay */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          background:
            "linear-gradient(135deg, rgba(255,180,100,0.06) 0%, transparent 50%, rgba(30,40,80,0.08) 100%)",
          pointerEvents: "none",
          zIndex: 50,
        }}
      />
      {/* Subtle vignette */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          background:
            "radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.35) 100%)",
          pointerEvents: "none",
          zIndex: 51,
        }}
      />
      {/* Film grain texture overlay */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          opacity: 0.03,
          background:
            "repeating-conic-gradient(rgba(255,255,255,0.1) 0%, transparent 0.5%)",
          pointerEvents: "none",
          zIndex: 52,
          mixBlendMode: "overlay",
        }}
      />
    </div>
  );
};
