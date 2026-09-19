import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { toEasing } from "./easing";

export type TitleBarProps = {
  title: string;
};

export const TitleBar: React.FC<TitleBarProps> = ({ title }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const inDurationFrames = theme.motion.inDuration * fps;
  const easing = toEasing(theme.motion.inEase);

  const opacity = interpolate(frame, [0, inDurationFrames], [0, 1], {
    easing,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const translateY = interpolate(frame, [0, inDurationFrames], [-40, 0], {
    easing,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        left: theme.layout.safeSide,
        right: theme.layout.safeSide,
        top: theme.layout.titleTop,
        display: "flex",
        justifyContent: "center",
        opacity,
        transform: `translateY(${translateY}px)`,
      }}
    >
      <h1
        style={{
          margin: 0,
          fontFamily: `${theme.typography.titleFamily}, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif`,
          fontWeight: theme.typography.titleWeight,
          fontSize: theme.typography.titleSize,
          lineHeight: 1.15,
          textAlign: "center",
          color: theme.colors.accent,
          textShadow: theme.stroke.shadow,
        }}
      >
        {title}
      </h1>
    </div>
  );
};
