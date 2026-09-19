import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { toEasing } from "./easing";

export type CaptionProps = {
  text: string;
};

// HyperFrames 회차템플릿(index.html)의 #caption과 같은 구조: 자막은 타이틀보다
// 0.4초 늦게 등장한다. 이 지연은 frame.md의 디자인 토큰이 아니라 두 요소의
// 등장 순서를 정하는 구조적 값이라 theme에 없다(HyperFrames 쪽도 tokens.css가
// 아니라 index.html에 data-start="0.4"로 하드코딩돼 있다).
const CAPTION_DELAY_SECONDS = 0.4;

export const Caption: React.FC<CaptionProps> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const localFrame = frame - CAPTION_DELAY_SECONDS * fps;
  const inDurationFrames = theme.motion.inDuration * fps;
  const easing = toEasing(theme.motion.inEase);

  const opacity = interpolate(localFrame, [0, inDurationFrames], [0, 1], {
    easing,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const translateY = interpolate(localFrame, [0, inDurationFrames], [30, 0], {
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
        bottom: theme.layout.captionBottom,
        display: "flex",
        justifyContent: "center",
        opacity,
        transform: `translateY(${translateY}px)`,
      }}
    >
      <p
        style={{
          margin: 0,
          fontFamily: `${theme.typography.captionFamily}, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif`,
          fontWeight: theme.typography.captionWeight,
          fontSize: theme.typography.captionSize,
          lineHeight: 1.25,
          textAlign: "center",
          color: theme.colors.fg,
          WebkitTextStroke: `${theme.stroke.captionOutline}px ${theme.colors.bg}`,
          paintOrder: "stroke fill",
        }}
      >
        {text}
      </p>
    </div>
  );
};
