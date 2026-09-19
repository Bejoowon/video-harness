import React from "react";
import { AbsoluteFill, staticFile } from "remotion";
import { Audio } from "@remotion/media";
import { theme } from "./theme";
import { TitleBar } from "./parts/TitleBar";
import { Caption } from "./parts/Caption";
import { SourceLabel } from "./parts/SourceLabel";

export type EpisodeProps = {
  title: string;
  caption: string;
  source: string;
  narration: string | null;
  durationInSeconds: number;
};

export const Episode: React.FC<EpisodeProps> = ({
  title,
  caption,
  source,
  narration,
}) => {
  return (
    <AbsoluteFill>
      {/* 배경 영상 자리: 실제 촬영본이 들어오기 전까지는 theme 배경색으로 채운다 */}
      <AbsoluteFill style={{ backgroundColor: theme.colors.bg }} />
      <TitleBar title={title} />
      <Caption text={caption} />
      <SourceLabel text={source} />
      {narration ? <Audio src={staticFile(narration)} /> : null}
    </AbsoluteFill>
  );
};
